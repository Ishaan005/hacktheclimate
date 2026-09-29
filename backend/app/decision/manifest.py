"""Explicit handoff gate for scenario, action, and metric decisions."""

from __future__ import annotations

from pathlib import Path
from datetime import timedelta
from typing import Literal

from pydantic import Field, model_validator

from .contracts import Contract, DecisionCase, ResolvedContext, utc
from .scenarios import load_scenario_catalogue

DEFAULT_MANIFEST = Path(__file__).resolve().parents[3] / "config/decision_contract_status.json"


class FactRequirement(Contract):
    field: str
    unit: str
    allowed_source_types: list[Literal["operator", "measurement", "forecast", "planning_model"]] = Field(min_length=1)
    cadence: Literal["once", "half_hour"]
    max_age_seconds: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_fact(self):
        if not self.field.strip() or not self.unit.strip():
            raise ValueError("required fact needs a field and unit")
        return self


class DecisionContractManifest(Contract):
    schema_version: Literal[1] = 1
    status: Literal["pending_review", "approved"]
    scenario_catalogue_reference: str | None = None
    approval_reference: str | None
    scenario_ids: list[str]
    action_ids: list[str]
    required_facts_by_scenario: dict[str, list[FactRequirement]]
    outcome_metrics_approved: bool

    @model_validator(mode="after")
    def valid_approval(self):
        if len(set(self.scenario_ids)) != len(self.scenario_ids) or len(set(self.action_ids)) != len(self.action_ids):
            raise ValueError("contract IDs must be unique")
        if set(self.required_facts_by_scenario) - set(self.scenario_ids):
            raise ValueError("required facts reference an unknown scenario")
        if any(len({fact.field for fact in facts}) != len(facts)
               for facts in self.required_facts_by_scenario.values()):
            raise ValueError("required facts must be unique within each scenario")
        if self.status == "approved" and (
            not self.approval_reference or not self.scenario_catalogue_reference
            or not self.scenario_ids or not self.action_ids
            or not self.outcome_metrics_approved
            or set(self.required_facts_by_scenario) != set(self.scenario_ids)
            or any(not facts for facts in self.required_facts_by_scenario.values())
        ):
            raise ValueError("approved contract needs source, scenarios, actions, metrics, and fact mappings")
        return self


def load_contract_manifest(path: Path = DEFAULT_MANIFEST) -> DecisionContractManifest:
    manifest = DecisionContractManifest.model_validate_json(path.read_text())
    if manifest.scenario_catalogue_reference:
        catalogue = load_scenario_catalogue()
        if (manifest.scenario_catalogue_reference != catalogue.source
            or set(manifest.scenario_ids) != {item.scenario_id for item in catalogue.definitions}):
            raise ValueError("manifest scenario IDs must match the locked catalogue")
    return manifest


def contract_gaps(manifest: DecisionContractManifest, case: DecisionCase) -> list[str]:
    gaps = []
    if case.cause_unknown:
        gaps.append("Limiting cause unknown; collect the scenario identification facts")
    unknown = sorted(set(case.scenario_ids) - set(manifest.scenario_ids))
    if unknown:
        gaps.append(f"Unknown scenario IDs: {', '.join(unknown)}")
    if manifest.status != "approved":
        gaps.append("Action, required-fact, and outcome-metric contracts are pending domain review")
    return gaps


def required_case_facts(manifest: DecisionContractManifest, case: DecisionCase) -> set[str]:
    if manifest.status != "approved":
        return set()
    return {fact.field for scenario in case.scenario_ids
            for fact in manifest.required_facts_by_scenario.get(scenario, [])}


def fact_gaps(manifest: DecisionContractManifest, context: ResolvedContext) -> list[str]:
    """Enforce reviewed unit, source type, cadence, and age on required facts."""
    if manifest.status != "approved":
        return []
    times = {utc(context.case.starts_at) + timedelta(minutes=30 * index) for index in range(48)}
    gaps = []
    for scenario in context.case.scenario_ids:
        for requirement in manifest.required_facts_by_scenario.get(scenario, []):
            valid_times = set()
            any_valid = False
            for item in context.values.get(requirement.field, []):
                evidence = item.evidence
                reference = evidence.observed_at if evidence.source_type == "measurement" else evidence.available_at
                if (item.status != "available" or evidence.unit != requirement.unit
                    or evidence.source_type not in requirement.allowed_source_types
                    or reference is None
                    or (utc(context.case.as_of) - utc(reference)).total_seconds() > requirement.max_age_seconds):
                    continue
                any_valid = True
                if evidence.valid_at is not None and utc(evidence.valid_at) in times:
                    valid_times.add(utc(evidence.valid_at))
            if requirement.cadence == "once" and not any_valid:
                gaps.append(f"{scenario}: required {requirement.field} needs a fresh {requirement.unit} value from an approved source")
            elif requirement.cadence == "half_hour" and len(valid_times) != 48:
                gaps.append(f"{scenario}: required {requirement.field} covers {len(valid_times)}/48 half-hours with approved units and sources")
    return gaps

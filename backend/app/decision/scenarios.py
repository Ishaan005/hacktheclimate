"""Locked product scenario catalogue; intake fields are not approved safety inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import Contract, ResolvedContext

CATALOGUE_PATH = Path(__file__).resolve().parents[3] / "config/decision_scenarios_v1.json"
SCENARIO_IDS = frozenset({"T1", "T2", "T3", "T4", "H1", "H2", "H3", "H4", "SNSP"})


class ScenarioDefinition(Contract):
    scenario_id: str
    family: Literal["transmission", "high_frequency_minimum_generation", "snsp"]
    name: str
    selection: str
    scope: str
    variants: list[str] = Field(min_length=1)
    intake_fields: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_definition(self):
        if not self.name.strip() or not self.selection.strip() or not self.scope.strip():
            raise ValueError("scenario definition needs a name, selection rule, and scope")
        if len(set(self.intake_fields)) != len(self.intake_fields):
            raise ValueError("scenario intake fields must be unique")
        return self


class ScenarioCatalogue(Contract):
    schema_version: Literal[1] = 1
    status: Literal["locked"]
    source: str
    definitions: list[ScenarioDefinition]

    @model_validator(mode="after")
    def complete_catalogue(self):
        ids = [item.scenario_id for item in self.definitions]
        if len(ids) != len(set(ids)) or set(ids) != SCENARIO_IDS:
            raise ValueError("scenario catalogue must contain T1-T4, H1-H4, and SNSP exactly once")
        for item in self.definitions:
            family = "transmission" if item.scenario_id.startswith("T") else "snsp" if item.scenario_id == "SNSP" else "high_frequency_minimum_generation"
            if item.family != family:
                raise ValueError(f"{item.scenario_id} has the wrong family")
        if not self.source.strip():
            raise ValueError("scenario catalogue needs a source")
        return self


def load_scenario_catalogue(path: Path = CATALOGUE_PATH) -> ScenarioCatalogue:
    return ScenarioCatalogue.model_validate_json(path.read_text())


class ScenarioIntakeCoverage(Contract):
    scenario_id: str
    recorded_fields: list[str]
    missing_fields: list[str]
    classification_verified: bool = False


def assess_scenario_intake(context: ResolvedContext, catalogue: ScenarioCatalogue) -> list[ScenarioIntakeCoverage]:
    """Show recorded identification facts; presence alone never verifies a limiting cause."""
    definitions = {item.scenario_id: item for item in catalogue.definitions}
    assessments = []
    for scenario_id in context.case.scenario_ids:
        definition = definitions.get(scenario_id)
        if definition is None:
            continue
        recorded = []
        missing = []
        for field in definition.intake_fields:
            values = context.values.get(field, [])
            found = any(
                item.status == "available" and item.evidence.value is not None
                and (scenario_id != "H1" or field != "measured_frequency_hz"
                     or (item.evidence.source_type == "measurement"
                         and item.evidence.unit == "Hz"
                         and isinstance(item.evidence.value, (int, float))
                         and not isinstance(item.evidence.value, bool)))
                for item in values
            )
            (recorded if found else missing).append(field)
        assessments.append(ScenarioIntakeCoverage(
            scenario_id=scenario_id, recorded_fields=recorded, missing_fields=missing,
        ))
    return assessments

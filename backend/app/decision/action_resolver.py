"""Deterministic mapping from locked scenarios to issue #51 action families."""

from __future__ import annotations

from typing import Iterable, Literal

from pydantic import Field

from .actions import ActionCatalogue, ExecutionStatus, load_action_catalogue
from .contracts import Contract, DecisionCase
from .scenarios import SCENARIO_IDS


class ResolvedAction(Contract):
    action_id: str
    name: str
    execution_status: ExecutionStatus
    eligibility: Literal["eligible", "partial"]
    matched_scenarios: list[str]
    uncovered_scenarios: list[str]
    required_parameters: list[str]
    required_evidence_fields: list[str]
    required_safety_rules: list[str]
    missing_parameters: list[str] = Field(default_factory=list)
    missing_evidence_fields: list[str] = Field(default_factory=list)

    @property
    def planning_ready(self) -> bool:
        return (
            self.eligibility == "eligible"
            and self.execution_status == "planning_supported"
            and not self.missing_parameters
            and not self.missing_evidence_fields
        )


def resolve_action_ids(
    scenario_ids: Iterable[str],
    *,
    catalogue: ActionCatalogue | None = None,
    available_parameters: Iterable[str] = (),
    available_evidence_fields: Iterable[str] = (),
) -> list[ResolvedAction]:
    """Resolve valid action families without asking an LLM to invent candidates.

    Multi-scenario cases return the union for operator visibility. An action is
    fully eligible only when it applies to every active scenario; otherwise it
    is labelled partial and cannot enter the planning executor as a sole action.
    """
    active = list(dict.fromkeys(scenario_ids))
    unknown = sorted(set(active) - SCENARIO_IDS)
    if unknown:
        raise ValueError(f"unknown locked scenario IDs: {', '.join(unknown)}")
    if not active:
        return []

    catalogue = catalogue or load_action_catalogue()
    parameters = set(available_parameters)
    evidence = set(available_evidence_fields)
    resolved: list[ResolvedAction] = []
    for action in catalogue.actions:
        matched = sorted(set(active).intersection(action.applicable_scenarios))
        if not matched:
            continue
        uncovered = sorted(set(active) - set(action.applicable_scenarios))
        resolved.append(ResolvedAction(
            action_id=action.action_id,
            name=action.name,
            execution_status=action.execution_status,
            eligibility="partial" if uncovered else "eligible",
            matched_scenarios=matched,
            uncovered_scenarios=uncovered,
            required_parameters=list(action.required_parameters),
            required_evidence_fields=list(action.required_evidence_fields),
            required_safety_rules=action.safety_rules_for(matched),
            missing_parameters=sorted(set(action.required_parameters) - parameters),
            missing_evidence_fields=sorted(set(action.required_evidence_fields) - evidence),
        ))
    return sorted(resolved, key=lambda item: item.action_id)


def resolve_case_actions(
    case: DecisionCase,
    *,
    catalogue: ActionCatalogue | None = None,
    available_parameters: Iterable[str] = (),
    available_evidence_fields: Iterable[str] = (),
) -> list[ResolvedAction]:
    if case.cause_unknown:
        return []
    return resolve_action_ids(
        case.scenario_ids,
        catalogue=catalogue,
        available_parameters=available_parameters,
        available_evidence_fields=available_evidence_fields,
    )

"""Evaluate one supplied decision case against the local planning network."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from backend.app.decision import (
    DecisionCase, EvidenceValue, calculate_current_plan, load_action_catalogue,
    load_contract_manifest, load_demo_policy, resolve_action_ids, resolve_case_context,
)
from backend.app.decision.contracts import Contract, utc
from backend.app.network import NetworkCase
from backend.app.network_forecast import _parse_time, validate_forecast_rows
from backend.app.network_scenarios import Asset
from backend.app.operator_view import build_operator_view
from backend.app.safety import CheckResult, SafetyResult


class OperatorEvaluationRequest(Contract):
    decision_case: DecisionCase
    forecast_available_at: datetime
    forecast_version: str
    forecast_evidence_reference: str
    forecast_rows: list[dict[str, Any]] = Field(min_length=48, max_length=48)
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceValue] = Field(default_factory=list)

    @model_validator(mode="after")
    def aligned_window(self):
        validate_forecast_rows(self.forecast_rows, as_of=utc(self.decision_case.as_of))
        issued = _parse_time(str(self.forecast_rows[0]["issue_time"]))
        available = utc(self.forecast_available_at)
        if available < issued or available > utc(self.decision_case.as_of):
            raise ValueError("forecast bundle was not available at the decision time")
        if not self.forecast_version.strip() or not self.forecast_evidence_reference.strip():
            raise ValueError("forecast version and evidence reference are required")
        first = _parse_time(str(self.forecast_rows[0]["valid_time"]))
        if first != utc(self.decision_case.starts_at):
            raise ValueError("forecast must start at the decision case start")
        return self


def _safety_result(payload: dict[str, Any]) -> SafetyResult:
    return SafetyResult(
        overall=payload["overall"],
        **{name: CheckResult(**payload[name]) for name in (
            "thermal", "islanding", "snsp", "voltage", "inertia", "rocof",
        )},
    )


def _candidate_contract_action_id(candidate: dict[str, Any]) -> str:
    # The existing network candidate schema predates the decision contract and
    # can only express paired flexible demand + renewable output. Preserve that
    # input shape while allowing future executors to identify their action family.
    return str(candidate.get("contract_action_id") or "FLEX_LOAD")


def _available_evidence_fields(
    request: OperatorEvaluationRequest,
    context,
) -> set[str]:
    available = {
        field
        for field, values in context.values.items()
        if any(item.status == "available" for item in values)
    }
    if all("recoverable_renewable_mw" in row for row in request.forecast_rows):
        available.add("recoverable_renewable_mw")
    return available


def _resolve_operator_actions(
    request: OperatorEvaluationRequest,
    context,
) -> tuple[list, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Resolve issue #51 families and admit only supported instances to the executor."""
    catalogue = load_action_catalogue()
    base_evidence = _available_evidence_fields(request, context)
    broad = resolve_action_ids(
        request.decision_case.scenario_ids,
        catalogue=catalogue,
        available_evidence_fields=base_evidence,
    )
    broad_by_id = {item.action_id: item for item in broad}
    candidates_by_family: dict[str, list[dict[str, Any]]] = {}
    candidate_rejections: list[dict[str, Any]] = []
    for candidate in request.action_candidates:
        family = _candidate_contract_action_id(candidate)
        if family not in {action.action_id for action in catalogue.actions}:
            candidate_rejections.append({
                "action_id": str(candidate.get("action_id", "")),
                "contract_action_id": family,
                "reason": "Unknown decision action family",
            })
            continue
        candidates_by_family.setdefault(family, []).append(candidate)

    resolved = []
    planning_candidates: list[dict[str, Any]] = []
    executed_families: set[str] = set()
    for action in broad:
        family_candidates = candidates_by_family.get(action.action_id, [])
        parameters = {key for candidate in family_candidates for key in candidate}
        detailed = next(item for item in resolve_action_ids(
            request.decision_case.scenario_ids,
            catalogue=catalogue,
            available_parameters=parameters,
            available_evidence_fields=base_evidence,
        ) if item.action_id == action.action_id)
        resolved.append(detailed)

        for candidate in family_candidates:
            missing = sorted(set(detailed.required_parameters) - set(candidate))
            reasons = []
            if detailed.eligibility != "eligible":
                reasons.append("Action family does not cover every active scenario")
            if detailed.execution_status != "planning_supported":
                reasons.append(f"Action family execution status is {detailed.execution_status}")
            if detailed.missing_evidence_fields:
                reasons.append(
                    "Missing required evidence: " + ", ".join(detailed.missing_evidence_fields)
                )
            if missing:
                reasons.append("Missing required parameters: " + ", ".join(missing))
            if reasons:
                candidate_rejections.append({
                    "action_id": str(candidate.get("action_id", "")),
                    "contract_action_id": detailed.action_id,
                    "reason": "; ".join(reasons),
                })
                continue
            planning_candidates.append(candidate)
            executed_families.add(detailed.action_id)

    unavailable = []
    for action in resolved:
        if action.action_id in executed_families:
            continue
        reasons = []
        if action.eligibility == "partial":
            reasons.append(
                "Does not cover active scenarios: " + ", ".join(action.uncovered_scenarios)
            )
        if action.execution_status != "planning_supported":
            reasons.append(f"Execution status is {action.execution_status}")
        if not candidates_by_family.get(action.action_id):
            reasons.append("No physical action instance was supplied")
        if action.missing_evidence_fields:
            reasons.append("Missing evidence: " + ", ".join(action.missing_evidence_fields))
        if action.missing_parameters and candidates_by_family.get(action.action_id):
            reasons.append("Missing parameters: " + ", ".join(action.missing_parameters))
        unavailable.append({
            **action.model_dump(mode="json"),
            "reason": "; ".join(reasons) or "Not admitted to the planning executor",
        })

    return resolved, planning_candidates, unavailable, {
        "catalogue_status": catalogue.status,
        "catalogue_source": catalogue.source,
        "candidate_rejections": candidate_rejections,
    }


def evaluate_operator_case(
    request: OperatorEvaluationRequest,
    case: NetworkCase,
    reviewed_crosswalk: list[dict[str, Any]],
    *,
    planned_outage: Asset,
) -> dict[str, Any]:
    """Return baseline, scenario-valid action effects, and evidence-gated rankings."""
    context = resolve_case_context(
        request.decision_case, request.evidence,
        required_fields=("constraint_mwh", "curtailment_mwh"),
    )
    resolved_actions, planning_candidates, unavailable_actions, action_contract = (
        _resolve_operator_actions(request, context)
    )
    view = build_operator_view(
        case, request.forecast_rows, reviewed_crosswalk, planning_candidates,
        action_catalog_available=bool(planning_candidates),
        planned_outage=planned_outage,
    )
    by_time: dict[datetime, SafetyResult] = {
        _parse_time(row["valid_time"]): _safety_result(row["network"]["safety"])
        for row in view["forecast"]
    }
    baseline = calculate_current_plan(context, load_demo_policy(), planning_safety=by_time)
    contract = load_contract_manifest()

    mismatches = []
    for forecast_row in view["forecast"]:
        target = _parse_time(forecast_row["valid_time"])
        matches = [item for item in context.values.get("constraint_mwh", [])
                   if item.status == "available" and item.evidence.valid_at is not None
                   and utc(item.evidence.valid_at) == target]
        value = matches[0].evidence.value if matches else None
        if isinstance(value, (int, float)) and abs(value - forecast_row["expected_constraint_mwh"]) > 1e-6:
            mismatches.append(forecast_row["valid_time"])
    if mismatches:
        raise ValueError(
            "current-plan constraint evidence disagrees with network forecast at "
            + ", ".join(mismatches[:3])
        )

    family_by_instance = {
        str(candidate["action_id"]): _candidate_contract_action_id(candidate)
        for candidate in planning_candidates
    }
    resolved_by_id = {item.action_id: item for item in resolved_actions}
    actions = []
    for action in view["actions"]:
        family = family_by_instance[action["action_id"]]
        resolution = resolved_by_id[family]
        actions.append({
            **action,
            "contract_action_id": family,
            "required_safety_rules": resolution.required_safety_rules,
        })

    exploratory = sorted(
        actions,
        key=lambda action: (-action["modeled_capture_upper_bound_mwh"], action["action_id"]),
    )
    blockers = []
    if contract.status != "approved":
        blockers.append("Scenario, action and outcome contract is pending domain review")
    if baseline.status != "metrics_complete":
        blockers.append("Current-plan constraint and curtailment MWh are not both available for all 48 intervals")
    if not baseline.safety.safety_gate_passed:
        blockers.append(f"Current-plan safety gate is {baseline.safety.overall}")
    if not actions:
        blockers.append("No scenario-valid planning-supported action candidates were supplied")
    if any(action["safety_overall"] != "PASS" for action in actions):
        blockers.append("One or more evaluated actions lack a full safety PASS")
    blockers.append("No validated locational model converts network effects into expected avoided dispatch-down MWh")

    return {
        "case_id": request.decision_case.case_id,
        "decision_contract_status": contract.status,
        "action_contract": action_contract,
        "eligible_actions": [item.model_dump(mode="json") for item in resolved_actions],
        "unavailable_actions": unavailable_actions,
        "case_provenance": {
            **view["network"],
            "forecast_available_at": request.forecast_available_at.isoformat(),
            "forecast_version": request.forecast_version,
            "forecast_evidence_reference": request.forecast_evidence_reference,
        },
        "current_plan": baseline.model_dump(mode="json"),
        "forecast": view["forecast"],
        "actions": actions,
        "ranked_modeled_capture_bounds": [
            {"action_id": action["action_id"],
             "contract_action_id": action["contract_action_id"],
             "modeled_capture_upper_bound_mwh": action["modeled_capture_upper_bound_mwh"],
             "safety_overall": action["safety_overall"]}
            for action in exploratory
        ],
        "ranked_expected_avoided_dispatch_down": [],
        "recommendation": None,
        "blocking_reasons": blockers,
        "health": view["health"],
    }

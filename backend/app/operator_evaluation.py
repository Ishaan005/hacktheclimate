"""Evaluate one supplied decision case against the local planning network."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from backend.app.decision import (
    DecisionCase, EvidenceValue, calculate_current_plan, load_contract_manifest, load_demo_policy,
    resolve_case_context,
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


def evaluate_operator_case(
    request: OperatorEvaluationRequest,
    case: NetworkCase,
    reviewed_crosswalk: list[dict[str, Any]],
    *,
    planned_outage: Asset,
) -> dict[str, Any]:
    """Return baseline, paired action effects, and evidence-gated rankings.

    Forecast rows drive network states. Separately sourced energy evidence
    drives the current-plan MWh baseline; neither is inferred from DC flows.
    """
    view = build_operator_view(
        case, request.forecast_rows, reviewed_crosswalk, request.action_candidates,
        action_catalog_available=bool(request.action_candidates),
        planned_outage=planned_outage,
    )
    by_time: dict[datetime, SafetyResult] = {
        _parse_time(row["valid_time"]): _safety_result(row["network"]["safety"])
        for row in view["forecast"]
    }
    context = resolve_case_context(
        request.decision_case, request.evidence,
        required_fields=("constraint_mwh", "curtailment_mwh"),
    )
    baseline = calculate_current_plan(context, load_demo_policy(), planning_safety=by_time)
    contract = load_contract_manifest()
    # The national MWh row and the baseline's constraint evidence may come from
    # different producers. Refuse to present them as one comparable estimate.
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
    actions = view["actions"]
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
        blockers.append("No reviewed action candidates were supplied")
    if any(action["safety_overall"] != "PASS" for action in actions):
        blockers.append("One or more actions lack a full safety PASS")
    blockers.append("No validated locational model converts network effects into expected avoided dispatch-down MWh")
    return {
        "case_id": request.decision_case.case_id,
        "decision_contract_status": contract.status,
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
             "modeled_capture_upper_bound_mwh": action["modeled_capture_upper_bound_mwh"],
             "safety_overall": action["safety_overall"]}
            for action in exploratory
        ],
        "ranked_expected_avoided_dispatch_down": [],
        "recommendation": None,
        "blocking_reasons": blockers,
        "health": view["health"],
    }

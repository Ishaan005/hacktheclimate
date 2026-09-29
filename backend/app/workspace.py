"""Adapter from the reviewed frontend case to the existing decision backend.

The React ScenarioWorkspace is the presentation contract. This route maps its
reviewed OperatorCase into the locked decision scenario IDs, runs the existing
forecast/network/action evaluation, and maps the result back to the
WorkspaceScenario shape. Missing evidence stays UNKNOWN and never becomes a
recommendation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from typing import Any, Mapping

from fastapi import APIRouter
from pydantic import Field

from .decision.contracts import Contract, DecisionCase, EvidenceValue
from .demo_cases import (
    evaluate_west_outage_demo,
    fallback_west_outage_demo,
    matches_west_outage_demo,
)
from .network import load_case
from .network_actions import load_action_candidates
from .network_forecast import (
    DEFAULT_CASE_DIR,
    DEFAULT_CROSSWALK_PATH,
    DEFAULT_INPUT_PATH,
    DEFAULT_PLANNED_OUTAGE,
    _parse_time,
    load_forecast_inputs,
    load_reviewed_crosswalk,
)
from .operator_evaluation import OperatorEvaluationRequest, evaluate_operator_case

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION_CANDIDATE_PATH = Path(
    os.getenv(
        "NETWORK_ACTION_CANDIDATES",
        REPO_ROOT / "data/processed/network_action_candidates.json",
    )
)

router = APIRouter(prefix="/v1/workspace", tags=["operator workspace"])

_FRONTEND_SCENARIOS = {
    "local_network_constraint",
    "system_wide_curtailment",
    "planned_outage_exposure",
    "cause_unknown",
}


class WorkspaceEvaluateRequest(Contract):
    case: dict[str, Any] = Field(default_factory=dict)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _case_fact(case: Mapping[str, Any], key: str) -> Any:
    facts = case.get("facts", {})
    fact = facts.get(key) if isinstance(facts, Mapping) else None
    return fact.get("value") if isinstance(fact, Mapping) else None


def _locked_scenarios(case: Mapping[str, Any]) -> list[str]:
    """Resolve the coarse reviewed UI classification into locked issue #47 IDs.

    T2/T4 and H1-H4 require an explicit cue. A reviewed local-network case with
    no outage/contingency cue maps to T1; a reviewed planned-outage case maps to
    T3 unless a further credible-failure cue is explicit.
    """
    text = str(case.get("originalText", "")).casefold()
    raw = case.get("scenarios", [])
    coarse = {
        str(value)
        for value in raw
        if str(value) in _FRONTEND_SCENARIOS
    }
    resolved: list[str] = []

    local = "local_network_constraint" in coarse
    outage = "planned_outage_exposure" in coarse or any(
        term in text for term in ("planned outage", "outage", "out of service", "equipment out")
    )
    contingency = any(
        term in text
        for term in ("n-1", "contingency", "another loss", "another trip", "single failure")
    )
    if local or outage:
        if outage and contingency:
            resolved.append("T4")
        elif outage:
            resolved.append("T3")
        elif contingency:
            resolved.append("T2")
        else:
            resolved.append("T1")

    if "system_wide_curtailment" in coarse:
        if "snsp" in text:
            resolved.append("SNSP")
        if any(term in text for term in ("high frequency", "over-frequency", "overfrequency")):
            resolved.append("H1")
        if any(term in text for term in (
            "minimum generation", "minimum conventional", "minimum unit", "inertia",
        )):
            resolved.append("H2")
        if "reserve" in text:
            resolved.append("H3")
        if "ramp" in text:
            resolved.append("H4")

    return list(dict.fromkeys(resolved))


def _status(value: str | None) -> str:
    if value == "PASS":
        return "within_modelled_limit"
    if value in {"FAIL", "BREACH"}:
        return "breach"
    return "unknown"


def _unknown_guardrails(reason: str) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "baseline": "unknown",
            "postAction": "unknown",
            "margin": None,
            "timestamp": None,
            "note": reason,
        }
        for name in (
            "transmission_line",
            "thermal_capacity",
            "snsp",
            "scope",
            "min_generation",
        )
    ]


def _fallback_scenario(
    case: Mapping[str, Any],
    reason: str,
    *,
    scenario_ids: list[str] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    supplied = _case_fact(case, "expected_dispatch_down_mwh")
    baseline = float(supplied) if isinstance(supplied, (int, float)) else None
    suffix = f" — {' + '.join(scenario_ids)}" if scenario_ids else ""
    return {
        "id": str(case.get("id") or f"case-{_iso(now)}"),
        "title": f"Advisory planning screen{suffix}",
        "intervalStart": _iso(now),
        "intervalEnd": _iso(now + timedelta(hours=24)),
        "source": "live",
        "modelRunAt": None,
        "summary": reason,
        "keywords": [],
        "binding": None,
        "action": None,
        "noActionReason": reason,
        "baseline": {
            "securityResult": "unknown",
            "dispatchDownWasteMwh": baseline,
        },
        "postAction": None,
        "impact": None,
        "guardrails": _unknown_guardrails(reason),
    }


def _binding_type(scenario_ids: list[str]) -> str:
    if any(item.startswith("T") for item in scenario_ids):
        return "Thermal capacity"
    if "SNSP" in scenario_ids:
        return "SNSP"
    if "H1" in scenario_ids:
        return "High frequency"
    if "H2" in scenario_ids:
        return "Minimum conventional generation"
    if "H3" in scenario_ids:
        return "Reserve requirement"
    if "H4" in scenario_ids:
        return "Ramping"
    return "Planning screen"


def _peak_row(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = result.get("forecast", [])
    if not isinstance(rows, list) or not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            row.get("network", {}).get("max_dc_loading_proxy_pct")
            if row.get("network", {}).get("max_dc_loading_proxy_pct") is not None
            else -1.0,
            float(row.get("expected_constraint_mwh", 0.0)),
        ),
    )


def _no_action_reason(result: Mapping[str, Any]) -> str:
    best_id = result.get("best_modeled_capture_bundle")
    options = {
        str(item.get("bundle_id")): item
        for item in result.get("bundle_options", [])
        if isinstance(item, Mapping)
    }
    best = options.get(str(best_id))
    blockers = [str(item) for item in result.get("blocking_reasons", [])]

    if best is not None and best_id != "BASELINE":
        capture = float(best.get("modeled_capture_upper_bound_mwh", 0.0))
        safety = str(best.get("safety_overall", "UNKNOWN"))
        lead = (
            f"Highest modeled capture option is {best_id} "
            f"({capture:.1f} MWh upper bound, safety {safety}), "
            "but it is not a recommendation."
        )
        return " ".join([lead, *blockers[:3]])
    if blockers:
        return "No action is recommended. " + " ".join(blockers[:3])
    return "No action has complete evidence for recommendation."


def _workspace_scenario(
    case: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    scenario_ids: list[str],
) -> dict[str, Any]:
    peak = _peak_row(result)
    if peak is None:
        return _fallback_scenario(
            case,
            "The planning evaluation returned no forecast intervals.",
            scenario_ids=scenario_ids,
        )

    network = peak["network"]
    safety = network["safety"]
    loading = network.get("max_dc_loading_proxy_pct")
    worst_asset = network.get("worst_asset")
    metric = (
        f"{worst_asset} · {float(loading):.1f}% of rate A"
        if worst_asset is not None and loading is not None
        else "No rated network loading available"
    )
    margin = f"{100.0 - float(loading):+.1f} pp to rate A" if loading is not None else None

    current_plan = result.get("current_plan", {})
    baseline_total = current_plan.get("expected_dispatch_down_mwh")
    supplied_total = _case_fact(case, "expected_dispatch_down_mwh")
    if baseline_total is None and isinstance(supplied_total, (int, float)):
        baseline_total = float(supplied_total)

    baseline_status = _status(current_plan.get("safety", {}).get("overall"))
    thermal_status = _status(safety.get("thermal", {}).get("status"))
    snsp_status = _status(safety.get("snsp", {}).get("status"))
    confidence = peak.get("confidence", {})
    issue_time = confidence.get("forecast_issue_time") if isinstance(confidence, Mapping) else None
    area = _case_fact(case, "affected_area")

    if any(item.startswith("T") for item in scenario_ids):
        binding_status = thermal_status
    elif "SNSP" in scenario_ids:
        binding_status = snsp_status
    else:
        binding_status = baseline_status

    return {
        "id": str(case.get("id")),
        "title": f"{_binding_type(scenario_ids)} advisory — {' + '.join(scenario_ids)}",
        "intervalStart": str(result["forecast"][0]["valid_time"]),
        "intervalEnd": _iso(
            _parse_time(str(result["forecast"][0]["valid_time"])) + timedelta(hours=24)
        ),
        "source": "live",
        "modelRunAt": issue_time,
        "summary": (
            "Evidence-gated planning result using the configured forecast bundle "
            "and TYTFS planning case. The operator description is not proof that "
            "a named asset matches the configured model asset; missing checks "
            "remain unknown."
        ),
        "keywords": [],
        "binding": {
            "type": _binding_type(scenario_ids),
            "metric": metric,
            "location": str(area) if area is not None else None,
            "margin": margin,
            "status": binding_status,
        },
        # The decision backend intentionally leaves recommendation null until
        # every required safety check passes and avoided dispatch-down is
        # validated. Do not turn the exploratory bundle ranking into an action.
        "action": None,
        "noActionReason": _no_action_reason(result),
        "baseline": {
            "securityResult": baseline_status,
            "dispatchDownWasteMwh": baseline_total,
        },
        "postAction": None,
        "impact": None,
        "guardrails": [
            {
                "name": "transmission_line",
                "baseline": thermal_status,
                "postAction": "unknown",
                "margin": margin,
                "timestamp": str(peak["valid_time"]),
                "note": safety.get("thermal", {}).get("reason"),
            },
            {
                "name": "thermal_capacity",
                "baseline": thermal_status,
                "postAction": "unknown",
                "margin": margin,
                "timestamp": str(peak["valid_time"]),
                "note": (
                    "DC loading/rating screen; voltage and reactive-power "
                    "effects are not established."
                ),
            },
            {
                "name": "snsp",
                "baseline": snsp_status,
                "postAction": "unknown",
                "margin": None,
                "timestamp": str(peak["valid_time"]),
                "note": safety.get("snsp", {}).get("reason"),
            },
            {
                "name": "scope",
                "baseline": "unknown",
                "postAction": "unknown",
                "margin": None,
                "timestamp": None,
                "note": (
                    "The national forecast does not establish a locational "
                    "causal constraint."
                ),
            },
            {
                "name": "min_generation",
                "baseline": "unknown",
                "postAction": "unknown",
                "margin": None,
                "timestamp": None,
                "note": (
                    "Minimum-unit evidence is not supplied by the current "
                    "network screen."
                ),
            },
        ],
    }


def _constraint_evidence(rows: list[dict[str, Any]]) -> list[EvidenceValue]:
    """Build only evidence present in the configured forecast bundle."""
    issue = _parse_time(str(rows[0]["issue_time"]))
    source = str(rows[0]["forecast_source"])
    evidence: list[EvidenceValue] = []
    for row in rows:
        evidence.append(EvidenceValue(
            field="constraint_mwh",
            value=float(row["expected_constraint_mwh"]),
            unit="MWh per half-hour",
            source_type="forecast",
            source=source,
            source_version=source,
            issued_at=issue,
            available_at=issue,
            valid_at=_parse_time(str(row["valid_time"])),
            max_age_seconds=86400,
        ))
        if row.get("expected_curtailment_mwh") is not None:
            evidence.append(EvidenceValue(
                field="curtailment_mwh",
                value=float(row["expected_curtailment_mwh"]),
                unit="MWh per half-hour",
                source_type="forecast",
                source=source,
                source_version=source,
                issued_at=issue,
                available_at=issue,
                valid_at=_parse_time(str(row["valid_time"])),
                max_age_seconds=86400,
            ))
    return evidence


def _evaluate_live_case(case_payload: dict[str, Any]) -> dict[str, Any]:
    scenario_ids = _locked_scenarios(case_payload)
    if not scenario_ids:
        return _fallback_scenario(
            case_payload,
            (
                "The reviewed facts do not identify one of the locked "
                "T1–T4, H1–H4 or SNSP scenarios. No action was evaluated."
            ),
        )

    # Explicit golden-path demo: only Ballylickey + outage descriptions
    # use the packaged synthetic network. All normal cases continue to the
    # configured planning inputs below.
    if matches_west_outage_demo(case_payload):
        try:
            return evaluate_west_outage_demo(case_payload, scenario_ids)
        except Exception:
            return fallback_west_outage_demo(case_payload, scenario_ids)

    now = datetime.now(timezone.utc)
    try:
        rows = load_forecast_inputs(DEFAULT_INPUT_PATH, as_of=now)
        network_case = load_case(DEFAULT_CASE_DIR)
        crosswalk = load_reviewed_crosswalk(DEFAULT_CROSSWALK_PATH)
    except (FileNotFoundError, ValueError) as exc:
        return _fallback_scenario(
            case_payload,
            f"Planning evaluation unavailable: {exc}",
            scenario_ids=scenario_ids,
        )

    action_candidates: list[dict[str, Any]] = []
    if ACTION_CANDIDATE_PATH.is_file():
        try:
            action_candidates = load_action_candidates(ACTION_CANDIDATE_PATH)
        except (OSError, ValueError) as exc:
            return _fallback_scenario(
                case_payload,
                f"Action catalogue unavailable: {exc}",
                scenario_ids=scenario_ids,
            )

    issue = _parse_time(str(rows[0]["issue_time"]))
    start = _parse_time(str(rows[0]["valid_time"]))
    decision_case = DecisionCase(
        case_id=str(case_payload.get("id") or f"case-{_iso(now)}"),
        scenario_ids=scenario_ids,
        location=(
            str(_case_fact(case_payload, "affected_area"))
            if _case_fact(case_payload, "affected_area") is not None
            else None
        ),
        asset_ids=[],
        as_of=now,
        starts_at=start,
        ends_at=start + timedelta(hours=24),
    )
    request = OperatorEvaluationRequest(
        decision_case=decision_case,
        forecast_available_at=issue,
        forecast_version=str(rows[0]["forecast_source"]),
        forecast_evidence_reference=str(DEFAULT_INPUT_PATH),
        forecast_rows=rows,
        action_candidates=action_candidates,
        evidence=_constraint_evidence(rows),
    )

    try:
        result = evaluate_operator_case(
            request,
            network_case,
            crosswalk,
            planned_outage=DEFAULT_PLANNED_OUTAGE,
        )
    except ValueError as exc:
        return _fallback_scenario(
            case_payload,
            f"Planning evaluation could not complete: {exc}",
            scenario_ids=scenario_ids,
        )
    return _workspace_scenario(case_payload, result, scenario_ids=scenario_ids)


@router.post("/evaluate")
def workspace_evaluate(request: WorkspaceEvaluateRequest) -> dict[str, Any]:
    """Return the existing frontend SolverResult scenario shape."""
    return {"kind": "scenario", "scenario": _evaluate_live_case(request.case)}

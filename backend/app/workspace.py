"""Backend adapter for the existing operator workspace UI.

The React workspace is intentionally treated as the presentation contract:
plain-language intake returns its reviewed-case shape, and evaluation returns
the existing WorkspaceScenario shape. The adapter delegates physical action
screening to the decision/network backend and preserves UNKNOWN rather than
inventing missing evidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
from typing import Any, Mapping

from fastapi import APIRouter
from pydantic import Field

from .decision.contracts import Contract, DecisionCase, EvidenceValue, utc
from .gfs_forecast import DEFAULT_OUTPUT_DIR, load_current_forecast
from .network import load_case
from .network_actions import load_action_candidates
from .network_forecast import (
    DEFAULT_CASE_DIR, DEFAULT_CROSSWALK_PATH, DEFAULT_INPUT_PATH,
    DEFAULT_PLANNED_OUTAGE, _parse_time, load_forecast_inputs,
    load_reviewed_crosswalk,
)
from .operator_evaluation import OperatorEvaluationRequest, evaluate_operator_case

REPO_ROOT = Path(__file__).resolve().parents[2]
GFS_FORECAST_PATH = DEFAULT_OUTPUT_DIR / "latest.json"
ACTION_CANDIDATE_PATH = Path(
    os.getenv(
        "NETWORK_ACTION_CANDIDATES",
        REPO_ROOT / "data/processed/network_action_candidates.json",
    )
)

router = APIRouter(tags=["operator workspace"])

_FRONTEND_SCENARIOS = {
    "local_network_constraint",
    "system_wide_curtailment",
    "planned_outage_exposure",
    "cause_unknown",
}

_AREA_PATTERNS = (
    ("North-west", ("north-west", "north west", "northwest")),
    ("South-west", ("south-west", "south west", "southwest")),
    ("South-east", ("south-east", "south east", "southeast")),
    ("North-east", ("north-east", "north east", "northeast")),
    ("Midlands", ("midlands", "midland")),
    ("Dublin", ("dublin",)),
    ("West", ("west", "western")),
    ("South", ("south", "southern")),
    ("North", ("north", "northern")),
    ("All-island", ("all-island", "all island", "ireland-wide", "system-wide")),
)

_TIME_WINDOW = re.compile(
    r"(?P<start>\b(?:[01]\d|2[0-3]):[0-5]\d)\b\s*(?:-|–|—|to)\s*"
    r"(?P<end>\b(?:[01]\d|2[0-3]):[0-5]\d)\b",
    re.IGNORECASE,
)


class IntakeRequest(Contract):
    description: str = Field(min_length=1, max_length=4000)
    comparison_text: str | None = Field(default=None, max_length=4000)
    created_at: datetime


class WorkspaceEvaluateRequest(Contract):
    case: dict[str, Any]


def _iso(value: datetime) -> str:
    return utc(value).isoformat().replace("+00:00", "Z")


def _fact(
    key: str,
    value: Any,
    *,
    unit: str | None,
    source: str,
    source_name: str,
    as_of: datetime,
    status: str = "verified",
) -> dict[str, Any]:
    return {
        "key": key,
        "value": value,
        "unit": unit,
        "status": status,
        "source": source,
        "sourceName": source_name,
        "asOf": _iso(as_of),
        "history": [],
    }


def _scenario_families(text: str) -> list[str]:
    lowered = text.casefold()
    found: list[str] = []
    if any(word in lowered for word in (
        "snsp", "inertia", "frequency", "reserve", "minimum generation",
        "minimum conventional", "curtailment", "ramp",
    )):
        found.append("system_wide_curtailment")
    if any(word in lowered for word in (
        "line", "transformer", "overload", "thermal", "export limit",
        "network limit", "constraint", "corridor",
    )):
        found.append("local_network_constraint")
    if any(word in lowered for word in (
        "outage", "out of service", "maintenance", "equipment out",
    )):
        found.append("planned_outage_exposure")
    return found or ["cause_unknown"]


def _affected_area(text: str) -> str | None:
    lowered = text.casefold()
    for label, terms in _AREA_PATTERNS:
        if any(term in lowered for term in terms):
            return label
    return None


def _explicit_window(text: str) -> str | None:
    match = _TIME_WINDOW.search(text)
    if not match:
        return None
    return f"{match.group('start')}–{match.group('end')} UTC"


def _forecast_enrichment(as_of: datetime) -> dict[str, dict[str, Any]]:
    """Return only facts the national constraint product can honestly supply."""
    try:
        snapshot = load_current_forecast(GFS_FORECAST_PATH, as_of=as_of)
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        return {}
    rows = snapshot["forecasts"]
    if not rows:
        return {}
    first = rows[0]
    last = rows[-1]
    probability = max(float(row["event_probability"]) for row in rows) * 100.0
    expected_constraint = sum(float(row["expected_constraint_mwh"]) for row in rows)
    return {
        "event_window": _fact(
            "event_window",
            f"{first['target_time_utc']} – {last['target_time_utc']}",
            unit=None,
            source="forecast",
            source_name=str(snapshot["model"]["name"]),
            as_of=_parse_time(snapshot["decision_time_utc"]),
        ),
        "event_probability": _fact(
            "event_probability",
            probability,
            unit="%",
            source="forecast",
            source_name=str(snapshot["model"]["name"]),
            as_of=_parse_time(snapshot["decision_time_utc"]),
        ),
        # Keep this separate from dispatch-down. The live candidate predicts
        # national constraint only, so it must not fill expected_dispatch_down_mwh.
        "expected_constraint_mwh": _fact(
            "expected_constraint_mwh",
            expected_constraint,
            unit="MWh",
            source="forecast",
            source_name=str(snapshot["model"]["name"]),
            as_of=_parse_time(snapshot["decision_time_utc"]),
        ),
    }


def _case_from_description(
    description: str,
    *,
    created_at: datetime,
    comparison_text: str | None = None,
) -> dict[str, Any]:
    created_at = utc(created_at)
    facts = _forecast_enrichment(created_at)
    area = _affected_area(description)
    if area is not None:
        facts["affected_area"] = _fact(
            "affected_area", area, unit=None, source="operator",
            source_name="Operator description", as_of=created_at, status="supplied",
        )
    window = _explicit_window(description)
    if window is not None:
        facts["event_window"] = _fact(
            "event_window", window, unit=None, source="operator",
            source_name="Operator description", as_of=created_at, status="supplied",
        )
    case = {
        "id": f"case-{_iso(created_at)}",
        "originalText": description,
        "createdAt": _iso(created_at),
        "scenarios": _scenario_families(description),
        "facts": facts,
        "proposedAction": None,
        "comparison": None,
    }
    if comparison_text:
        case["comparison"] = {
            "kind": "situation",
            "originalText": comparison_text,
            "situation": _case_from_description(
                comparison_text, created_at=created_at, comparison_text=None,
            ),
        }
    return case


@router.post("/v1/intake")
def intake(request: IntakeRequest) -> dict[str, Any]:
    """Turn plain language into the exact reviewed-case object the UI already uses."""
    return {
        "case": _case_from_description(
            request.description,
            created_at=request.created_at,
            comparison_text=request.comparison_text,
        ),
        "extraction": "rules",
    }


def _case_fact(case: Mapping[str, Any], key: str) -> Any:
    fact = case.get("facts", {}).get(key)
    return fact.get("value") if isinstance(fact, Mapping) else None


def _locked_scenarios(case: Mapping[str, Any]) -> list[str]:
    """Resolve the reviewed coarse UI scenario into the locked #47 IDs."""
    text = str(case.get("originalText", "")).casefold()
    coarse = {
        str(value)
        for value in case.get("scenarios", [])
        if str(value) in _FRONTEND_SCENARIOS
    }
    resolved: list[str] = []

    local = bool(
        {"local_network_constraint", "planned_outage_exposure"}.intersection(coarse)
    )
    outage = "planned_outage_exposure" in coarse or any(
        term in text for term in ("outage", "out of service", "equipment out")
    )
    contingency = any(
        term in text
        for term in ("n-1", "contingency", "another loss", "another trip", "single failure")
    )
    if local:
        if outage and contingency:
            resolved.append("T4")
        elif outage:
            resolved.append("T3")
        elif contingency:
            resolved.append("T2")
        elif any(term in text for term in ("overload", "thermal", "export limit", "line", "transformer", "corridor")):
            resolved.append("T1")

    if "system_wide_curtailment" in coarse:
        if "snsp" in text:
            resolved.append("SNSP")
        if any(term in text for term in ("high frequency", "over-frequency", "overfrequency")):
            resolved.append("H1")
        if any(term in text for term in ("minimum generation", "minimum conventional", "minimum unit", "inertia")):
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


def _unknown_guardrails() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "baseline": "unknown",
            "postAction": "unknown",
            "margin": None,
            "timestamp": None,
            "note": "No supported calculation is available for this workspace result.",
        }
        for name in (
            "transmission_line", "thermal_capacity", "snsp", "scope", "min_generation",
        )
    ]


def _fallback_scenario(
    case: Mapping[str, Any],
    reason: str,
    *,
    scenario_ids: list[str] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    baseline = _case_fact(case, "expected_dispatch_down_mwh")
    baseline_value = float(baseline) if isinstance(baseline, (int, float)) else None
    suffix = f" ({', '.join(scenario_ids)})" if scenario_ids else ""
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
            "dispatchDownWasteMwh": baseline_value,
        },
        "postAction": None,
        "impact": None,
        "guardrails": _unknown_guardrails(),
    }


def _peak_row(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    rows = result.get("forecast", [])
    if not rows:
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


def _no_action_reason(result: Mapping[str, Any]) -> str:
    best_id = result.get("best_modeled_capture_bundle")
    options = {
        str(item.get("bundle_id")): item
        for item in result.get("bundle_options", [])
    }
    best = options.get(str(best_id))
    blockers = [str(item) for item in result.get("blocking_reasons", [])]
    if best and best_id != "BASELINE":
        capture = float(best.get("modeled_capture_upper_bound_mwh", 0.0))
        safety = str(best.get("safety_overall", "UNKNOWN"))
        lead = (
            f"Highest modeled capture option is {best_id} "
            f"({capture:.1f} MWh upper bound, safety {safety}), but it is not a recommendation."
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
            case, "The planning evaluation returned no forecast intervals.",
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
    margin = (
        f"{100.0 - float(loading):+.1f} pp to rate A"
        if loading is not None else None
    )
    baseline_total = result.get("current_plan", {}).get("expected_dispatch_down_mwh")
    supplied_total = _case_fact(case, "expected_dispatch_down_mwh")
    if baseline_total is None and isinstance(supplied_total, (int, float)):
        baseline_total = float(supplied_total)

    baseline_status = _status(result.get("current_plan", {}).get("safety", {}).get("overall"))
    thermal_status = _status(safety.get("thermal", {}).get("status"))
    snsp_status = _status(safety.get("snsp", {}).get("status"))
    issue_time = peak.get("confidence", {}).get("forecast_issue_time")
    area = _case_fact(case, "affected_area")

    return {
        "id": str(case.get("id")),
        "title": f"{_binding_type(scenario_ids)} advisory — {' + '.join(scenario_ids)}",
        "intervalStart": str(result["forecast"][0]["valid_time"]),
        "intervalEnd": _iso(_parse_time(str(result["forecast"][0]["valid_time"])) + timedelta(hours=24)),
        "source": "live",
        "modelRunAt": issue_time,
        "summary": (
            "Evidence-gated planning result using the current forecast bundle and "
            "the configured TYTFS planning case. Missing checks remain unknown."
        ),
        "keywords": [],
        "binding": {
            "type": _binding_type(scenario_ids),
            "metric": metric,
            "location": str(area) if area is not None else None,
            "margin": margin,
            "status": thermal_status if any(item.startswith("T") for item in scenario_ids) else (
                snsp_status if "SNSP" in scenario_ids else baseline_status
            ),
        },
        # operator_evaluation deliberately leaves recommendation null until
        # expected avoided dispatch-down and every required safety check pass.
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
                "note": "DC loading/rating screen; voltage and reactive-power effects are not established.",
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
                "note": "The national forecast does not establish a locational causal constraint.",
            },
            {
                "name": "min_generation",
                "baseline": "unknown",
                "postAction": "unknown",
                "margin": None,
                "timestamp": None,
                "note": "Minimum-unit evidence is not supplied by the current network screen.",
            },
        ],
    }


def _constraint_evidence(rows: list[dict[str, Any]], as_of: datetime) -> list[EvidenceValue]:
    evidence: list[EvidenceValue] = []
    issue = _parse_time(str(rows[0]["issue_time"]))
    source = str(rows[0]["forecast_source"])
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
            "The reviewed facts do not identify one of the locked T1–T4, H1–H4 or SNSP scenarios. No action was evaluated.",
        )

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

    issue = _parse_time(str(rows[0]["issue_time"]))
    start = _parse_time(str(rows[0]["valid_time"]))
    action_candidates: list[dict[str, Any]] = []
    if ACTION_CANDIDATE_PATH.is_file():
        try:
            action_candidates = load_action_candidates(ACTION_CANDIDATE_PATH)
        except (ValueError, OSError) as exc:
            return _fallback_scenario(
                case_payload,
                f"Action catalogue unavailable: {exc}",
                scenario_ids=scenario_ids,
            )

    decision_case = DecisionCase(
        case_id=str(case_payload.get("id") or f"case-{_iso(now)}"),
        scenario_ids=scenario_ids,
        location=(
            str(_case_fact(case_payload, "affected_area"))
            if _case_fact(case_payload, "affected_area") is not None else None
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
        evidence=_constraint_evidence(rows, now),
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


@router.post("/v1/workspace/evaluate")
def workspace_evaluate(request: WorkspaceEvaluateRequest) -> dict[str, Any]:
    """Return the SolverResult shape consumed by the existing React workspace."""
    return {"kind": "scenario", "scenario": _evaluate_live_case(request.case)}

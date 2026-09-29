"""One auditable envelope for forecasts, future network states and actions."""

from __future__ import annotations

from typing import Any

from backend.app.network import NetworkCase
from backend.app.network_actions import screen_actions
from backend.app.network_forecast import DEFAULT_PLANNED_OUTAGE, build_network_forecast
from backend.app.network_scenarios import Asset


def build_operator_view(
    case: NetworkCase,
    forecast_rows: list[dict[str, Any]],
    reviewed_crosswalk: list[dict[str, Any]],
    action_candidates: list[dict[str, Any]],
    *,
    action_catalog_available: bool,
    planned_outage: Asset = DEFAULT_PLANNED_OUTAGE,
) -> dict[str, Any]:
    forecast = build_network_forecast(
        case, forecast_rows, reviewed_crosswalk, planned_outage=planned_outage,
    )
    first_network = forecast[0]["network"]
    selected_contingency = (
        Asset(first_network["worst_contingency_type"], first_network["worst_contingency"])
        if first_network["worst_contingency"] is not None else None
    )
    actions = screen_actions(
        case, forecast_rows, reviewed_crosswalk, action_candidates,
        planned_outage=planned_outage,
        selected_contingency=selected_contingency,
    )
    missing = []
    if not action_catalog_available or not any(
        item.get("review_status") in {"accepted_proxy", "accepted_verified"}
        for item in action_candidates
    ):
        missing.append("reviewed flexible-action catalog")
    if not all(row.get("recoverable_renewable_mw") for row in forecast_rows):
        missing.append("regional recoverable renewable forecast")
    if not all(row.get("snsp_pct") is not None for row in forecast_rows):
        missing.append("point-in-time SNSP forecast")
    missing.append("validated locational avoided-constraint impact model")
    return {
        "forecast": forecast,
        "network": {
            "case_scenario_date": case.metadata.get("scenario_date"),
            "case_source_sha256": case.metadata.get("source_sha256"),
            "planned_outage": {"asset_type": planned_outage.asset_type, "asset_id": planned_outage.asset_id},
            "scope": "TYTFS planning-case DC scenario screen",
        },
        "actions": actions["evaluated"],
        "ranked_screening_pass_actions": actions["ranked_screening_pass_actions"],
        "recommendation": actions["recommendation"],
        "health": {
            "status": "incomplete" if missing or actions["recommendation"] is None else "ready",
            "forecast_issue_time": forecast[0]["confidence"]["forecast_issue_time"],
            "forecast_source": forecast[0]["confidence"]["forecast_source"],
            "missing_inputs": missing,
            "unsupported_safety_checks": ["voltage", "inertia", "rocof"],
            "recommendation_reason": actions["recommendation_reason"],
        },
    }

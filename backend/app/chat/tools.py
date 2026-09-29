"""Tools the assistant can call. Every number it reports must come from one of these."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _safe(fn):
    try:
        return fn()
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # ToolNode re-raises non-validation errors, which would kill the chat turn.
        logger.exception("Chat tool failed")
        return {"error": f"Tool failed: {type(exc).__name__}"}


@tool
def get_dispatch_down_forecast(target_timestamp: str) -> dict:
    """One-hour-ahead national dispatch-down risk for a single half-hour.

    target_timestamp: ISO UTC time on the hour or half hour between
    2026-01-01T01:00:00Z and 2026-01-31T23:30:00Z, e.g. "2026-01-24T01:00:00Z".
    Returns risk (low/elevated/high), event_probability (0-1),
    expected_dispatch_down_mwh and limitations.
    """
    from ..dispatch_down.predictor import get_dispatch_down_predictor

    return _safe(lambda: get_dispatch_down_predictor().predict(target_timestamp))


@tool
def get_dispatch_down_day(target_timestamp: str) -> dict:
    """All 48 half-hourly dispatch-down predictions for the UTC day containing target_timestamp.

    Use for questions about a whole day, peaks, or "which hours are worst".
    Returns {date, points: [{target_timestamp, event_probability, expected_dispatch_down_mwh}]}.
    """
    from ..dispatch_down.predictor import get_dispatch_down_predictor

    return _safe(lambda: get_dispatch_down_predictor().predict_day(target_timestamp))


@tool
def check_constraint(target_timestamp: str, horizon_hours: int = 1) -> dict:
    """Historical replay of national constraint (not total dispatch-down) for a target time.

    horizon_hours must be one of 1, 4, 6, 12, 24. Returns risk_level,
    event_probability, expected_constraint_mwh and an 80% interval.
    """
    if horizon_hours not in {1, 4, 6, 12, 24}:
        return {"error": "Supported horizons are 1, 4, 6, 12 and 24 hours."}
    from ..constraints.checker import get_constraint_checker

    return _safe(lambda: get_constraint_checker().check(target_timestamp, horizon_hours))


def _current_constraint_snapshot() -> dict:
    from ..gfs_forecast import DEFAULT_OUTPUT_DIR, load_current_forecast

    return load_current_forecast(DEFAULT_OUTPUT_DIR / "latest.json")


def _forecast_metadata(snapshot: dict) -> dict:
    return {
        "mode": "experimental_forward_forecast",
        "target": "national_constraint_mwh",
        "issue_time_utc": snapshot["issue_time_utc"],
        "generated_at_utc": snapshot["generated_at_utc"],
        "served_at_utc": snapshot["served_at_utc"],
        "forecast_end_utc": snapshot["forecast_end_utc"],
        "model": snapshot["model"]["name"],
        "model_sha256": snapshot["model"]["artifact_sha256"],
        "limitations": snapshot["limitations"],
    }


@tool
def get_current_constraint_forecast(target_timestamp: str) -> dict:
    """Checked experimental forward national constraint forecast for one future UTC half-hour.

    Use for a future target, not a January historical replay. The daily inference
    job must have published a current snapshot. This cannot predict curtailment,
    total dispatch-down, a location, network safety, or an operator action.
    target_timestamp must be ISO 8601 with a UTC offset, e.g. 2026-09-29T12:30:00Z.
    """
    try:
        target = datetime.fromisoformat(target_timestamp.replace("Z", "+00:00"))
        if target.tzinfo is None or target.utcoffset() != timezone.utc.utcoffset(target):
            raise ValueError("Target must have an explicit UTC offset.")
        if target.minute not in (0, 30) or target.second or target.microsecond:
            raise ValueError("Target must be exactly on a UTC half-hour.")
        snapshot = _current_constraint_snapshot()
        row = next((r for r in snapshot["forecasts"] if datetime.fromisoformat(r["target_time_utc"].replace("Z", "+00:00")) == target), None)
        if row is None:
            return {"error": "No current future constraint forecast for that target half-hour.", "forecast_end_utc": snapshot["forecast_end_utc"]}
        return {**_forecast_metadata(snapshot), "forecast": row}
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        return {"error": f"Checked forward constraint forecast unavailable: {exc}"}
    except Exception as exc:  # ToolNode re-raises these; report instead of failing the turn.
        logger.exception("Chat tool failed")
        return {"error": f"Checked forward constraint forecast unavailable: {type(exc).__name__}"}


@tool
def get_current_constraint_day() -> dict:
    """Summary of remaining half-hours in the current experimental national constraint forecast.

    Use for upcoming peaks or a general future outlook. Requires a checked,
    unexpired daily GFS inference result. This is constraint only, not total
    dispatch-down or a network action.
    """
    try:
        snapshot = _current_constraint_snapshot()
        rows = snapshot["forecasts"]
        return {
            **_forecast_metadata(snapshot),
            "remaining_intervals": len(rows),
            "sum_expected_constraint_mwh": round(sum(r["expected_constraint_mwh"] for r in rows), 1),
            "peak_intervals": sorted(rows, key=lambda r: r["expected_constraint_mwh"], reverse=True)[:5],
        }
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        return {"error": f"Checked forward constraint forecast unavailable: {exc}"}
    except Exception as exc:  # ToolNode re-raises these; report instead of failing the turn.
        logger.exception("Chat tool failed")
        return {"error": f"Checked forward constraint forecast unavailable: {type(exc).__name__}"}


@tool
def get_network_scenario(target_timestamp: str) -> dict:
    """Input-gated TYTFS planning-network DC scenario for one future UTC half-hour.

    Requires current 48-row upstream forecasts, a reviewed generator crosswalk,
    and an imported planning case. This is a scenario screen, not a live grid
    state, N-1 verdict, or safe action recommendation.
    """
    try:
        target = datetime.fromisoformat(target_timestamp.replace("Z", "+00:00"))
        if target.tzinfo is None or target.utcoffset() != timezone.utc.utcoffset(target):
            raise ValueError("Target must have an explicit UTC offset.")
        if target.minute not in (0, 30) or target.second or target.microsecond:
            raise ValueError("Target must be exactly on a UTC half-hour.")
        from ..network_forecast import build_network_forecast_from_files

        rows = build_network_forecast_from_files(as_of=datetime.now(timezone.utc))
        row = next((r for r in rows if datetime.fromisoformat(r["valid_time"].replace("Z", "+00:00")) == target), None)
        if row is None:
            return {"error": "No current planning-network scenario for that target half-hour."}
        return {**row, "mode": "planning_network_dc_scenario", "limitations": [
            "TYTFS planning case and DC proxy, not current operational topology or a thermal-security verdict.",
            "No safe dispatch action or avoided-energy impact follows from this scenario alone.",
        ]}
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        return {"error": f"Planning-network scenario unavailable: {exc}"}
    except Exception as exc:  # ToolNode re-raises these; report instead of failing the turn.
        logger.exception("Chat tool failed")
        return {"error": f"Planning-network scenario unavailable: {type(exc).__name__}"}


@tool
def get_scenario_actions(scenario_ids: list[str]) -> dict:
    """Return the deterministic issue #51 action families for locked scenario IDs.

    Use only T1, T2, T3, T4, H1, H2, H3, H4 or SNSP. This tool determines
    which action families are in scope; it does not prove an action is available,
    safe or recommendable.
    """
    try:
        from ..decision import load_action_catalogue, resolve_action_ids

        catalogue = load_action_catalogue()
        actions = resolve_action_ids(scenario_ids, catalogue=catalogue)
        return {
            "mode": "decision_action_contract",
            "catalogue_status": catalogue.status,
            "source": catalogue.source,
            "scenario_ids": scenario_ids,
            "actions": [action.model_dump(mode="json") for action in actions],
            "limitations": [
                "Eligibility comes from the working issue #51 contract; domain approval is still pending.",
                "planning_supported means an executor exists, not that a specific asset is available or safe.",
                "A recommendation still requires exact action inputs and passing safety/evidence gates.",
            ],
        }
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        return {"error": f"Decision action contract unavailable: {exc}"}


FORECAST_TOOLS = [get_dispatch_down_forecast, get_dispatch_down_day, check_constraint,
                  get_current_constraint_forecast, get_current_constraint_day, get_network_scenario,
                  get_scenario_actions]

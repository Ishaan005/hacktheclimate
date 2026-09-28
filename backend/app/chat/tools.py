"""Tools the assistant can call. Every number it reports must come from one of these."""
from __future__ import annotations

from langchain_core.tools import tool


def _safe(fn, *args):
    try:
        return fn(*args)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}


@tool
def get_dispatch_down_forecast(target_timestamp: str) -> dict:
    """One-hour-ahead national dispatch-down risk for a single half-hour.

    target_timestamp: ISO UTC time on the hour or half hour between
    2026-01-01T01:00:00Z and 2026-01-31T23:30:00Z, e.g. "2026-01-24T01:00:00Z".
    Returns risk (low/elevated/high), event_probability (0-1),
    expected_dispatch_down_mwh and limitations.
    """
    from ..dispatch_down.predictor import get_dispatch_down_predictor

    return _safe(get_dispatch_down_predictor().predict, target_timestamp)


@tool
def get_dispatch_down_day(target_timestamp: str) -> dict:
    """All 48 half-hourly dispatch-down predictions for the UTC day containing target_timestamp.

    Use for questions about a whole day, peaks, or "which hours are worst".
    Returns {date, points: [{target_timestamp, event_probability, expected_dispatch_down_mwh}]}.
    """
    from ..dispatch_down.predictor import get_dispatch_down_predictor

    return _safe(get_dispatch_down_predictor().predict_day, target_timestamp)


@tool
def check_constraint(target_timestamp: str, horizon_hours: int = 1) -> dict:
    """National *constraint* (not total dispatch-down) forecast for a target time.

    horizon_hours must be one of 1, 4, 6, 12, 24. Returns risk_level,
    event_probability, expected_constraint_mwh and an 80% interval.
    """
    if horizon_hours not in {1, 4, 6, 12, 24}:
        return {"error": "Supported horizons are 1, 4, 6, 12 and 24 hours."}
    from ..constraints.checker import get_constraint_checker

    return _safe(get_constraint_checker().check, target_timestamp, horizon_hours)


FORECAST_TOOLS = [get_dispatch_down_forecast, get_dispatch_down_day, check_constraint]

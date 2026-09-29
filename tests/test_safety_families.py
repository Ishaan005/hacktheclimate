from __future__ import annotations

import pytest

from backend.app.safety import (
    CheckResult,
    combine_checks,
    evaluate_transmission_family,
)


def _solve(flow_mw: float, rating_mva: float = 100.0) -> dict:
    return {
        "status": "ok",
        "flows": [
            {
                "asset_type": "branch",
                "asset_id": "A",
                "flow_mw": flow_mw,
                "rating_mva": rating_mva,
                "loading_pct": abs(flow_mw) / rating_mva * 100,
            }
        ],
    }


def test_not_applicable_is_excluded_from_rollup():
    assert combine_checks({
        "required": CheckResult("PASS", "required check"),
        "irrelevant": CheckResult("NOT_APPLICABLE", "not active for this case"),
    }) == "PASS"
    assert combine_checks({
        "irrelevant": CheckResult("NOT_APPLICABLE", "not active for this case"),
    }) == "UNKNOWN"


def test_transmission_family_exposes_margin_and_keeps_missing_timing_unknown():
    result = evaluate_transmission_family(
        _solve(70.0),
        _solve(60.0),
        base_contingency_solve=_solve(85.0),
        action_contingency_solve=_solve(80.0),
    )

    assert result.checks["current_forecast_thermal_margin"].status == "PASS"
    assert result.checks["current_forecast_thermal_margin"].value == pytest.approx(40.0)
    assert result.checks["worst_credible_failure_margin"].value == pytest.approx(20.0)
    assert result.checks["new_bottleneck"].status == "PASS"
    assert result.checks["time_to_relief"].status == "UNKNOWN"
    assert result.overall == "UNKNOWN"


def test_transmission_family_fails_when_candidate_creates_new_bottleneck():
    result = evaluate_transmission_family(
        _solve(90.0),
        _solve(110.0),
        base_contingency_solve=_solve(90.0),
        action_contingency_solve=_solve(110.0),
        relief_timing_verified=True,
    )

    assert result.checks["current_forecast_thermal_margin"].status == "FAIL"
    assert result.checks["new_bottleneck"].status == "FAIL"
    assert result.checks["new_bottleneck"].asset_id == "A"
    assert result.overall == "FAIL"


def test_transmission_family_can_pass_when_all_four_gates_are_evidenced():
    result = evaluate_transmission_family(
        _solve(70.0),
        _solve(60.0),
        base_contingency_solve=_solve(85.0),
        action_contingency_solve=_solve(80.0),
        relief_timing_verified=True,
    )
    assert result.overall == "PASS"
    assert result.recommendable


def test_transmission_family_checks_shifted_bottleneck_in_contingency_state():
    result = evaluate_transmission_family(
        _solve(70.0),
        _solve(60.0),
        base_contingency_solve=_solve(90.0),
        action_contingency_solve=_solve(110.0),
        relief_timing_verified=True,
    )

    assert result.checks["current_forecast_thermal_margin"].status == "PASS"
    assert result.checks["worst_credible_failure_margin"].status == "FAIL"
    assert result.checks["new_bottleneck"].status == "FAIL"
    assert result.checks["new_bottleneck"].asset_id == "A"

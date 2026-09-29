from __future__ import annotations

from copy import deepcopy

import pytest

from backend.app.network_actions import rank_pass_actions, screen_actions
from backend.app.network_scenarios import Asset
from backend.app.operator_view import build_operator_view
from backend.app.safety import CheckResult, evaluate_safety
from test_network_forecast import _case, _crosswalk, _rows


def _candidate() -> dict:
    return {
        "action_id": "illustrative-flex-1",
        "load_bus_id": 3,
        "renewable_bus_id": 2,
        "allocation_region": "South-West",
        "generation_type": "wind",
        "power_mw": 10.0,
        "available_from": "2026-09-29T00:00:00Z",
        "available_until": "2026-09-29T01:00:00Z",
        "review_status": "accepted_proxy",
        "evidence_reference": "synthetic-test-action",
    }


def test_safety_fail_precedes_unknown_and_missing_evidence_never_passes():
    incomplete = evaluate_safety({
        "status": "ok", "flows": [
            {"loading_pct": 50.0}, {"loading_pct": None},
        ],
    })
    assert incomplete.overall == "UNKNOWN"
    assert incomplete.thermal.status == "UNKNOWN"
    assert incomplete.voltage.status == "UNKNOWN"
    assert not incomplete.recommendable

    failed = evaluate_safety({"status": "islanded", "flows": []}, snsp_pct=80.0)
    assert failed.overall == "FAIL"
    assert failed.islanding.status == "FAIL"
    assert failed.snsp.status == "FAIL"

    proxy_breach = evaluate_safety({"status": "ok", "flows": [{"loading_pct": 101.0}]})
    assert proxy_breach.thermal.status == "FAIL"
    assert proxy_breach.overall == "FAIL"


def test_all_required_checks_need_explicit_evidence_for_pass():
    complete = evaluate_safety(
        {"status": "ok", "flows": [{"loading_pct": 60.0}]},
        snsp_pct=60.0,
        externally_verified={
            name: CheckResult("PASS", "Reviewed external result.", f"verified-{name}-record")
            for name in ("voltage", "inertia", "rocof")
        },
    )
    assert complete.overall == "PASS"
    assert complete.recommendable
    with pytest.raises(ValueError, match="evidence"):
        evaluate_safety(
            {"status": "ok", "flows": [{"loading_pct": 60.0}]},
            externally_verified={"voltage": CheckResult("PASS", "No source.")},
        )


def test_action_changes_nodal_injections_and_unknown_is_not_ranked():
    rows = deepcopy(_rows())
    for row in rows:
        row["recoverable_renewable_mw"] = {"South-West": {"wind": 10.0}}
    screened = screen_actions(
        _case(), rows, _crosswalk(), [_candidate()],
        planned_outage=Asset("branch", "1:3:1"),
    )
    action = screened["evaluated"][0]
    assert action["modeled_capture_upper_bound_mwh"] == pytest.approx(10.0)
    assert action["expected_avoided_constraint_mwh"] is None
    assert action["safety_overall"] == "UNKNOWN"
    assert action["intervals"][0]["applied_mw"] == pytest.approx(10.0)
    effect = action["intervals"][0]["network_effect"]["planned_outage"]
    assert effect["base"]["max_dc_loading_proxy_pct"] != effect["with_action"]["max_dc_loading_proxy_pct"]
    assert screened["ranked_screening_pass_actions"] == []
    assert screened["recommendation"] is None


def test_action_safety_includes_selected_n_minus_one():
    rows = deepcopy(_rows())
    for row in rows:
        row["recoverable_renewable_mw"] = {"South-West": {"wind": 10.0}}
    screened = screen_actions(
        _case(), rows, _crosswalk(), [_candidate()],
        planned_outage=Asset("branch", "1:3:1"),
        selected_contingency=Asset("branch", "2:4:1"),
    )
    interval = screened["evaluated"][0]["intervals"][0]
    assert interval["safety"]["selected_n_minus_one"] is not None
    assert interval["network_effect"]["selected_n_minus_one"]["asset_id"] == "2:4:1"
    assert interval["safety"]["overall"] != "PASS"


def test_action_requires_explicit_recoverable_mw_and_pass_only_ranking():
    screened = screen_actions(
        _case(), _rows(), _crosswalk(), [_candidate()],
        planned_outage=Asset("branch", "1:3:1"),
    )
    assert screened["evaluated"][0]["modeled_capture_upper_bound_mwh"] == 0
    assert screened["evaluated"][0]["safety_overall"] == "UNKNOWN"
    ranked = rank_pass_actions([
        {"action_id": "unknown", "safety_overall": "UNKNOWN", "modeled_capture_upper_bound_mwh": 100},
        {"action_id": "small", "safety_overall": "PASS", "modeled_capture_upper_bound_mwh": 5},
        {"action_id": "large", "safety_overall": "PASS", "modeled_capture_upper_bound_mwh": 10},
    ])
    assert [row["action_id"] for row in ranked] == ["large", "small"]


def test_operator_view_exposes_missing_evidence_without_recommendation():
    view = build_operator_view(
        _case(), _rows(), _crosswalk(), [],
        action_catalog_available=False,
        planned_outage=Asset("branch", "1:3:1"),
    )
    assert len(view["forecast"]) == 48
    assert view["forecast"][0]["network"]["safety"]["overall"] == "UNKNOWN"
    assert view["recommendation"] is None
    assert view["health"]["status"] == "incomplete"
    assert "reviewed flexible-action catalog" in view["health"]["missing_inputs"]

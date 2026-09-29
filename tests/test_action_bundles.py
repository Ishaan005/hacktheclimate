from __future__ import annotations

from copy import deepcopy

import pytest

from backend.app.decision import generate_action_bundles
from backend.app.network_actions import screen_action_bundles
from backend.app.network_scenarios import Asset
from test_network_forecast import _case, _crosswalk, _rows
from test_network_safety_actions import _candidate


def _candidate_two() -> dict:
    candidate = deepcopy(_candidate())
    candidate["action_id"] = "illustrative-flex-2"
    candidate["power_mw"] = 10.0
    return candidate



def _redispatch_candidate(action_id: str = "redispatch-1") -> dict:
    return {
        "action_id": action_id,
        "contract_action_id": "GENERATOR_REDISPATCH",
        "source_asset_id": "GEN-1",
        "replacement_asset_id": "GEN-2",
        "source_bus_id": 1,
        "replacement_bus_id": 2,
        "power_mw": 10.0,
        "source_down_headroom_mw": 20.0,
        "replacement_up_headroom_mw": 20.0,
        "source_ramp_limit_mw": 20.0,
        "replacement_ramp_limit_mw": 20.0,
        "available_from": "2026-09-29T00:00:00Z",
        "available_until": "2026-09-29T01:00:00Z",
        "review_status": "accepted_proxy",
        "evidence_reference": "synthetic-redispatch-evidence",
    }


def test_bundle_generation_includes_baseline_and_all_compatible_combinations():
    candidates = [_candidate(), _candidate_two()]
    generated = generate_action_bundles(candidates)
    assert [bundle.bundle_id for bundle in generated.bundles] == [
        "BASELINE",
        "BUNDLE:illustrative-flex-1",
        "BUNDLE:illustrative-flex-2",
        "BUNDLE:illustrative-flex-1+illustrative-flex-2",
    ]
    assert generated.bundles[0].is_baseline
    assert generated.rejected == []


def test_explicit_conflicts_are_rejected_before_network_solve():
    first = _candidate()
    second = _candidate_two()
    first["conflicts_with"] = [second["action_id"]]
    generated = generate_action_bundles([first, second])
    assert "BUNDLE:illustrative-flex-1+illustrative-flex-2" not in {
        bundle.bundle_id for bundle in generated.bundles
    }
    assert generated.rejected
    assert "explicitly conflicts" in generated.rejected[0]["reasons"][0]


def test_bundle_screen_shares_recoverable_renewable_budget():
    rows = deepcopy(_rows())
    for row in rows:
        row["recoverable_renewable_mw"] = {"South-West": {"wind": 10.0}}
    candidates = [_candidate(), _candidate_two()]
    generated = generate_action_bundles(candidates)
    pair = next(
        bundle for bundle in generated.bundles
        if len(bundle.action_instance_ids) == 2
    )
    screened = screen_action_bundles(
        _case(), rows, _crosswalk(), candidates, [pair.model_dump(mode="json")],
        planned_outage=Asset("branch", "1:3:1"),
    )
    result = screened["evaluated"][0]

    # Both actions request 10 MW over two half-hours, but there is only 10 MW
    # of recoverable renewable opportunity. The bundle must not claim 20 MW.
    first_interval = result["intervals"][0]
    assert first_interval["applied_mw"] == pytest.approx(10.0)
    assert sum(first_interval["action_allocations_mw"].values()) == pytest.approx(10.0)
    assert result["modeled_capture_upper_bound_mwh"] == pytest.approx(10.0)
    assert result["expected_avoided_dispatch_down_mwh"] is None


def test_bundle_screen_rejects_baseline_as_network_intervention():
    rows = deepcopy(_rows())
    for row in rows:
        row["recoverable_renewable_mw"] = {"South-West": {"wind": 10.0}}
    baseline = generate_action_bundles([_candidate()]).bundles[0]
    with pytest.raises(ValueError, match="non-baseline bundles only"):
        screen_action_bundles(
            _case(), rows, _crosswalk(), [_candidate()],
            [baseline.model_dump(mode="json")],
            planned_outage=Asset("branch", "1:3:1"),
        )


def test_redispatch_changes_network_but_gets_no_direct_capture_credit():
    rows = deepcopy(_rows())
    candidate = _redispatch_candidate()
    generated = generate_action_bundles([candidate])
    bundle = next(item for item in generated.bundles if not item.is_baseline)
    screened = screen_action_bundles(
        _case(), rows, _crosswalk(), [candidate], [bundle.model_dump(mode="json")],
        planned_outage=Asset("branch", "1:3:1"),
    )
    result = screened["evaluated"][0]
    first = result["intervals"][0]
    assert first["applied_mw"] == pytest.approx(10.0)
    assert first["renewable_capture_mw"] == pytest.approx(0.0)
    assert result["modeled_capture_upper_bound_mwh"] == pytest.approx(0.0)
    effect = first["network_effect"]["planned_outage"]["flow_changes"]
    assert effect["changed_asset_count"] > 0\n    transmission = first["safety"]["families"]["transmission"]\n    assert transmission["checks"]["current_forecast_thermal_margin"]["value"] is not None\n    assert transmission["checks"]["time_to_relief"]["status"] == "UNKNOWN"


def test_mixed_flex_and_redispatch_bundle_credits_only_recovered_renewable():
    rows = deepcopy(_rows())
    for row in rows:
        row["recoverable_renewable_mw"] = {"South-West": {"wind": 10.0}}
    flex = _candidate()
    redispatch = _redispatch_candidate()
    generated = generate_action_bundles([flex, redispatch])
    pair = next(item for item in generated.bundles if len(item.action_instance_ids) == 2)
    screened = screen_action_bundles(
        _case(), rows, _crosswalk(), [flex, redispatch],
        [pair.model_dump(mode="json")],
        planned_outage=Asset("branch", "1:3:1"),
    )
    result = screened["evaluated"][0]
    first = result["intervals"][0]
    assert first["applied_mw"] == pytest.approx(20.0)
    assert first["renewable_capture_mw"] == pytest.approx(10.0)
    assert first["action_allocations_mw"]["redispatch-1"] == pytest.approx(10.0)
    assert result["modeled_capture_upper_bound_mwh"] == pytest.approx(10.0)
    assert result["expected_avoided_dispatch_down_mwh"] is None


def test_overlapping_redispatch_assets_are_not_combined():
    first = _redispatch_candidate("redispatch-1")
    second = _redispatch_candidate("redispatch-2")
    second["replacement_asset_id"] = "GEN-3"
    second["replacement_bus_id"] = 1
    generated = generate_action_bundles([first, second])
    assert not any(len(bundle.action_instance_ids) == 2 for bundle in generated.bundles)
    assert any("share generator asset GEN-1" in reason
               for rejected in generated.rejected for reason in rejected["reasons"])

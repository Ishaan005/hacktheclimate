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

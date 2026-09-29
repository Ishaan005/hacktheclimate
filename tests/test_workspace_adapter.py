from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app import workspace


UTC = timezone.utc


def test_intake_returns_frontend_case_shape_and_locked_direction(monkeypatch):
    monkeypatch.setattr(workspace, "_forecast_enrichment", lambda _as_of: {
        "event_window": workspace._fact(
            "event_window", "2026-09-30T12:00:00Z – 2026-10-01T11:30:00Z",
            unit=None, source="forecast", source_name="test-forecast",
            as_of=datetime(2026, 9, 30, 6, tzinfo=UTC),
        ),
        "event_probability": workspace._fact(
            "event_probability", 72.0, unit="%", source="forecast",
            source_name="test-forecast", as_of=datetime(2026, 9, 30, 6, tzinfo=UTC),
        ),
    })
    case = workspace._case_from_description(
        "Line overload in the west after the outage",
        created_at=datetime(2026, 9, 30, 8, tzinfo=UTC),
    )
    assert case["scenarios"] == ["local_network_constraint", "planned_outage_exposure"]
    assert case["facts"]["affected_area"]["value"] == "West"
    assert case["facts"]["event_probability"]["value"] == 72.0
    assert workspace._locked_scenarios(case) == ["T3"]


def test_intake_can_identify_multiple_system_limits(monkeypatch):
    monkeypatch.setattr(workspace, "_forecast_enrichment", lambda _as_of: {})
    case = workspace._case_from_description(
        "SNSP and reserve are limiting all-island from 14:00 to 16:00",
        created_at=datetime(2026, 9, 30, 8, tzinfo=UTC),
    )
    assert case["scenarios"] == ["system_wide_curtailment"]
    assert case["facts"]["affected_area"]["value"] == "All-island"
    assert case["facts"]["event_window"]["value"] == "14:00–16:00 UTC"
    assert workspace._locked_scenarios(case) == ["SNSP", "H3"]


def test_unknown_locked_scenario_returns_structured_no_action(monkeypatch):
    case = {
        "id": "case-1",
        "originalText": "There is a problem in the west",
        "createdAt": "2026-09-30T08:00:00Z",
        "scenarios": ["local_network_constraint"],
        "facts": {"affected_area": {"value": "West"}},
    }
    result = workspace._evaluate_live_case(case)
    assert result["source"] == "live"
    assert result["action"] is None
    assert result["binding"] is None
    assert "do not identify" in result["noActionReason"]


def test_workspace_mapping_preserves_unknown_and_best_modeled_candidate():
    case = {
        "id": "case-1",
        "originalText": "Line overload in west after outage",
        "createdAt": "2026-09-30T08:00:00Z",
        "scenarios": ["local_network_constraint", "planned_outage_exposure"],
        "facts": {
            "affected_area": {"value": "West"},
            "expected_dispatch_down_mwh": {"value": 40.0},
        },
    }
    unknown = {"status": "UNKNOWN", "reason": "Missing evidence.", "evidence": None}
    result = {
        "forecast": [{
            "valid_time": "2026-09-30T09:00:00Z",
            "expected_constraint_mwh": 12.0,
            "confidence": {"forecast_issue_time": "2026-09-30T06:00:00Z"},
            "network": {
                "worst_asset": "1:2:1",
                "max_dc_loading_proxy_pct": 104.0,
                "safety": {
                    "thermal": {"status": "FAIL", "reason": "Rating exceeded.", "evidence": "dc"},
                    "snsp": unknown,
                },
            },
        }],
        "current_plan": {
            "expected_dispatch_down_mwh": None,
            "safety": {"overall": "UNKNOWN"},
        },
        "best_modeled_capture_bundle": "BUNDLE:flex-1+redispatch-1",
        "bundle_options": [{
            "bundle_id": "BUNDLE:flex-1+redispatch-1",
            "modeled_capture_upper_bound_mwh": 8.0,
            "safety_overall": "UNKNOWN",
        }],
        "blocking_reasons": ["Reserve evidence missing.", "Avoided-energy model unavailable."],
    }
    scenario = workspace._workspace_scenario(case, result, scenario_ids=["T3"])
    assert scenario["source"] == "live"
    assert scenario["binding"]["status"] == "breach"
    assert scenario["baseline"]["dispatchDownWasteMwh"] == pytest.approx(40.0)
    assert scenario["action"] is None
    assert "8.0 MWh upper bound" in scenario["noActionReason"]
    assert "not a recommendation" in scenario["noActionReason"]

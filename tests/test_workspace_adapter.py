from __future__ import annotations

import pytest

from backend.app import workspace


def test_reviewed_scenarios_map_to_locked_decision_ids():
    local = {
        "originalText": "Line overload in the west",
        "scenarios": ["local_network_constraint"],
        "facts": {},
    }
    outage = {
        "originalText": "Line overload during planned outage",
        "scenarios": ["local_network_constraint", "planned_outage_exposure"],
        "facts": {},
    }
    contingency = {
        "originalText": "Line is safe now but N-1 overloads the backup",
        "scenarios": ["local_network_constraint"],
        "facts": {},
    }
    combined = {
        "originalText": "SNSP and reserve are limiting all-island",
        "scenarios": ["system_wide_curtailment"],
        "facts": {},
    }
    assert workspace._locked_scenarios(local) == ["T1"]
    assert workspace._locked_scenarios(outage) == ["T3"]
    assert workspace._locked_scenarios(contingency) == ["T2"]
    assert workspace._locked_scenarios(combined) == ["SNSP", "H3"]


def test_unresolved_system_limit_returns_structured_no_action():
    case = {
        "id": "case-1",
        "originalText": "System-wide limit",
        "scenarios": ["system_wide_curtailment"],
        "facts": {"affected_area": {"value": "All-island"}},
    }
    result = workspace._evaluate_live_case(case)
    assert result["source"] == "live"
    assert result["action"] is None
    assert result["binding"] is None
    assert "do not identify" in result["noActionReason"]


def test_workspace_mapping_preserves_unknown_and_modeled_candidate_context():
    case = {
        "id": "case-1",
        "originalText": "Line overload in west after outage",
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
        "blocking_reasons": [
            "Reserve evidence missing.",
            "Avoided-energy model unavailable.",
        ],
    }
    scenario = workspace._workspace_scenario(case, result, scenario_ids=["T3"])
    assert scenario["source"] == "live"
    assert scenario["binding"]["status"] == "breach"
    assert scenario["baseline"]["dispatchDownWasteMwh"] == pytest.approx(40.0)
    assert scenario["action"] is None
    assert scenario["postAction"] is None
    assert "8.0 MWh upper bound" in scenario["noActionReason"]
    assert "not a recommendation" in scenario["noActionReason"]


def test_missing_planning_inputs_degrade_to_workspace_result(monkeypatch):
    case = {
        "id": "case-1",
        "originalText": "Line overload in west",
        "scenarios": ["local_network_constraint"],
        "facts": {"affected_area": {"value": "West"}},
    }

    def missing(*_args, **_kwargs):
        raise FileNotFoundError("network inputs")

    monkeypatch.setattr(workspace, "load_forecast_inputs", missing)
    result = workspace._evaluate_live_case(case)
    assert result["action"] is None
    assert result["baseline"]["securityResult"] == "unknown"
    assert "Planning evaluation unavailable" in result["noActionReason"]

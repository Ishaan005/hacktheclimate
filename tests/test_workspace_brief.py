from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.app.workspace_brief import WorkspaceAssessmentRequest, assess_workspace, workspace_brief
from backend.app.decision.contracts import EvidenceValue
from backend.app.decision.sources import EvidenceSourceResult


DECISION = datetime(2026, 9, 29, 10, tzinfo=timezone.utc)


def request_payload() -> dict:
    return {
        "decision_case": {
            "case_id": "operator-case-1", "scenario_ids": ["T2", "SNSP"],
            "location": "site-a", "as_of": DECISION.isoformat(),
            "starts_at": (DECISION + timedelta(minutes=30)).isoformat(),
            "ends_at": (DECISION + timedelta(hours=24, minutes=30)).isoformat(),
            "existing_instructions": [{
                "instruction_id": "wdt-1", "starts_at": DECISION.isoformat(),
                "ends_at": (DECISION + timedelta(hours=2)).isoformat(),
                "evidence_reference": "operator-log-1", "included_in_forecast": True,
            }],
        },
        "view": "site", "site_id": "site-a",
        "proposed_plan": {"steps": [{
            "step_id": "charge-1", "action_id": "STORAGE_CHARGE",
            "asset_or_party": "battery-a", "executor": "asset owner",
            "permission": "pending", "limiting_location_delta_mw": -5.0,
        }]},
        "operator_alternative": {"steps": [{
            "step_id": "transfer-1", "action_id": "INTERCONNECTOR_TRANSFER",
            "permission": "denied",
        }]},
    }


def evidence(field: str, value: float, *, available_at: datetime = DECISION, source: str = "feed-a") -> dict:
    return {"field": field, "value": value, "unit": "MW", "source_type": "measurement",
            "source": source, "source_version": "v1", "observed_at": available_at.isoformat(),
            "available_at": available_at.isoformat(), "max_age_seconds": 300}


def test_brief_uses_only_locked_scenarios():
    result = workspace_brief()
    assert {item["scenario_id"] for item in result["scenario_catalogue"]["definitions"]} == {
        "T1", "T2", "T3", "T4", "H1", "H2", "H3", "H4", "SNSP",
    }


def test_http_contract_is_exposed():
    client = TestClient(app)
    assert client.get("/v1/workspace/brief").status_code == 200
    response = client.post("/v1/workspace/assess", json=request_payload())
    assert response.status_code == 200
    assert response.json()["comparisons"]["proposed_plan"]["safety"]["status"] == "UNKNOWN"


def test_assessment_preserves_four_windows_all_island_checks_and_existing_instructions():
    request = WorkspaceAssessmentRequest.model_validate(request_payload())
    result = assess_workspace(request)
    assert [item["scenario_id"] for item in result["bindings"]] == ["T2", "SNSP"]
    assert len(result["comparisons"]) == 4
    assert all(item["window"] == result["window"] for item in result["comparisons"].values())
    assert all(item["active_instructions"][0]["instruction_id"] == "wdt-1"
               for item in result["comparisons"].values())
    proposal = result["comparisons"]["proposed_plan"]
    assert proposal["permission_state"] == "pending"
    assert proposal["safety"]["status"] == "UNKNOWN"
    assert proposal["plan_label"] == "Insufficient evidence"
    assert {item["family"] for item in proposal["checks"]} == {"transmission", "snsp", "action", "cross_family"}
    assert proposal["benefits"]["avoided_dispatch_down_mwh"]["value"] is None
    alternative = result["comparisons"]["operator_alternative"]
    assert alternative["safety"]["status"] == "FAIL"
    assert alternative["plan_label"] == "Unsafe"
    assert result["source_status"] == "no_live_connection"
    assert result["evidence"]["audit_persisted"] is False
    assert result["revision"] == assess_workspace(request)["revision"]


def test_golden_path_bridges_existing_planning_evaluator_into_new_workspace():
    payload = request_payload()
    payload["decision_case"]["scenario_ids"] = ["T3"]
    payload["description"] = (
        "Planned outage in the west is causing a line overload. "
        "High wind around Ballylickey is constrained for the next 2 hours. "
        "What can we do to reduce dispatch-down?"
    )
    payload["conditions"] = [{
        "scenario_id": "T3",
        "situation_key": "t_outage_overload",
        "reach": "local_area",
        "limiting_asset": "West export route",
        "outage_type": "planned",
        "time_setting": "forecast",
    }]
    payload["proposed_plan"] = {"steps": []}
    payload["operator_alternative"] = {"steps": []}

    result = assess_workspace(WorkspaceAssessmentRequest.model_validate(payload))

    assert result["source_status"] == "planning_case"
    proposal = result["comparisons"]["proposed_plan"]
    assert proposal["plan"]["steps"]
    assert proposal["plan"]["steps"][0]["action_id"] in {"FLEX_LOAD", "STORAGE_CHARGE"}
    assert proposal["benefits"]["constraint_mwh"]["value"] is not None
    assert proposal["benefits"]["avoided_dispatch_down_mwh"]["value"] is not None
    assert "Synthetic" in " ".join(result["evidence"]["assumptions"])


def test_conflicting_and_stale_facts_stay_noncurrent():
    payload = request_payload()
    payload["evidence"] = [
        evidence("demand_mw", 100), evidence("demand_mw", 110, source="feed-b"),
        evidence("normal_flow_mw", 120, available_at=DECISION - timedelta(hours=1)),
    ]
    result = assess_workspace(WorkspaceAssessmentRequest.model_validate(payload))
    facts = {item["field"]: item for item in result["facts"]}
    assert facts["demand_mw"]["state"] == "conflicting"
    assert facts["normal_flow_mw"]["state"] == "stale"
    assert "normal_flow_mw" in result["bindings"][0]["missing_fields"]


def test_explicit_case_context_fills_only_supported_intake_rows():
    payload = request_payload()
    payload["decision_case"]["scenario_ids"] = ["T3"]
    payload["decision_case"]["existing_instructions"] = []
    payload["description"] = "Planned outage is causing an overload for the next 2 hours."
    result = assess_workspace(WorkspaceAssessmentRequest.model_validate(payload))
    facts = {item["field"]: item for item in result["facts"]}
    assert facts["outage_type"]["value"] == "planned"
    assert facts["outage_type"]["source"] == "Operator description"
    assert facts["relevant_time_window"]["value"] == "Next 2 hours from decision time"
    assert facts["now_or_forecast"]["value"] == "forecast"
    assert facts["active_instructions"]["state"] == "missing"
    assert "instruction log" in facts["active_instructions"]["reason"]
    assert "asset mapping" in facts["limiting_equipment"]["reason"]
    assert facts["normal_flow_mw"]["state"] == "missing"
    assert result["comparisons"]["proposed_plan"]["safety"]["status"] == "UNKNOWN"


def test_checked_national_forecast_is_context_only(monkeypatch):
    from backend.app import workspace_brief as module

    payload = request_payload()
    payload["decision_case"]["scenario_ids"] = ["T3"]
    payload["decision_case"]["existing_instructions"] = []
    start = DECISION + timedelta(minutes=30)
    row = EvidenceValue(
        field="constraint_mwh", value=12.5, unit="MWh per half-hour",
        source_type="forecast", source="checked experimental GFS", source_version="test",
        available_at=DECISION, issued_at=DECISION - timedelta(hours=1),
        valid_at=start, max_age_seconds=86400, lower_bound=4, upper_bound=25,
    )
    monkeypatch.setattr(module, "load_checked_constraint", lambda _as_of: EvidenceSourceResult(
        source="checked GFS national constraint", status="available", values=[row]))
    result = assess_workspace(WorkspaceAssessmentRequest.model_validate(payload))
    assert "12.5 MWh per half-hour" in result["national_constraint_context"]
    assert "National context only" in result["national_constraint_context"]
    assert result["comparisons"]["current_plan"]["benefits"]["constraint_mwh"]["value"] is None
    assert result["comparisons"]["proposed_plan"]["safety"]["status"] == "UNKNOWN"


def test_golden_path_shows_synthetic_facts_without_filling_operational_gates():
    now = datetime.now(timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=30 * (now.minute // 30 + 1))
    payload = request_payload()
    payload["decision_case"].update({
        "scenario_ids": ["T3"], "as_of": now.isoformat(),
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=24)).isoformat(),
        "existing_instructions": [],
    })
    payload["description"] = "Planned outage near Ballylickey causes a line overload for the next 2 hours."
    payload["conditions"] = [{"scenario_id": "T3", "situation_key": "t_outage_overload"}]
    result = assess_workspace(WorkspaceAssessmentRequest.model_validate(payload))
    facts = {item["field"]: item for item in result["facts"]}
    assert facts["limiting_equipment"]["value"] == "3:4:1"
    assert facts["normal_flow_mw"]["value"] == pytest.approx(60)
    assert facts["planning_rate_a_mva"]["value"] == 55
    assert facts["planning_rate_a_mva"]["unit"] == "MVA"
    assert facts["outage_equipment"]["value"] == "1:3:1"
    assert all(facts[field]["state"] == "modeled" for field in (
        "limiting_equipment", "normal_flow_mw", "planning_rate_a_mva", "outage_equipment"))
    assert facts["normal_flow_limit_mw"]["state"] == "missing"
    assert facts["active_instructions"]["state"] == "missing"
    assert "normal_flow_mw" in result["bindings"][0]["missing_fields"]
    baseline_check = next(c for c in result["comparisons"]["current_plan"]["checks"] if c["check_id"] == "planning_transmission_line")
    proposed_check = next(c for c in result["comparisons"]["proposed_plan"]["checks"] if c["check_id"] == "planning_transmission_line")
    assert (baseline_check["value"], baseline_check["effective_limit"], baseline_check["margin"]) == (
        "109.1% of rate A", "100% of rate A", "-5.0 MW")
    assert (proposed_check["value"], proposed_check["margin"]) == ("81.8% of rate A", "+10.0 MW")
    assert "Synthetic DC baseline" in baseline_check["reason"]
    for column in ("current_plan", "no_new_instruction", "proposed_plan"):
        curtailment = result["comparisons"][column]["benefits"]["curtailment_mwh"]
        assert curtailment["value"] is None
    assert result["comparisons"]["proposed_plan"]["safety"]["status"] == "UNKNOWN"


def test_other_outage_does_not_inherit_ballylickey_demo_facts():
    now = datetime.now(timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=30 * (now.minute // 30 + 1))
    payload = request_payload()
    payload["decision_case"].update({
        "scenario_ids": ["T3"], "as_of": now.isoformat(),
        "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=24)).isoformat(),
        "existing_instructions": [],
    })
    payload["description"] = "An outage on another route causes a line overload."
    payload["conditions"] = [{"scenario_id": "T3"}]
    result = assess_workspace(WorkspaceAssessmentRequest.model_validate(payload))
    assert all(fact["state"] != "modeled" for fact in result["facts"])
    assert result["comparisons"]["proposed_plan"]["safety"]["status"] == "UNKNOWN"


def test_rejects_unknown_scenario_and_unordered_dependencies():
    payload = request_payload()
    payload["decision_case"]["scenario_ids"] = ["VOLTAGE"]
    with pytest.raises(ValidationError):
        WorkspaceAssessmentRequest.model_validate(payload)
    payload = request_payload()
    payload["proposed_plan"]["steps"][0]["depends_on"] = ["later-step"]
    with pytest.raises(ValidationError):
        WorkspaceAssessmentRequest.model_validate(payload)

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from backend.app.decision.contracts import DecisionCase, EvidenceValue
from backend.app.decision.evidence import resolve_case_context
from backend.app.decision.manifest import DecisionContractManifest, contract_gaps, fact_gaps, load_contract_manifest, required_case_facts
from backend.app.decision.scenarios import SCENARIO_IDS, assess_scenario_intake, load_scenario_catalogue
from backend.app.decision.policy import load_demo_policy
from backend.app.decision.service import evaluate_case
from backend.app.decision.sources import EvidenceSourceResult, load_checked_constraint
from backend.app.main import app
from backend.app.decision import routes as decision_routes

UTC = timezone.utc
client = TestClient(app)


def case_payload() -> dict:
    as_of = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=1)
    start = as_of.replace(minute=30 if as_of.minute >= 30 else 0) + timedelta(minutes=30)
    return {
        "case_id": "preview-1", "scenario_ids": ["T1"],
        "location": "illustrative-west", "asset_ids": [],
        "as_of": as_of.isoformat(), "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=24)).isoformat(),
        "existing_instructions": [],
    }


def checked_rows(case: DecisionCase) -> list[EvidenceValue]:
    return [EvidenceValue(
        field="constraint_mwh", value=10.0, unit="MWh per half-hour",
        source_type="forecast", source="checked-test-snapshot", source_version="test-model-hash",
        available_at=case.as_of - timedelta(minutes=1),
        issued_at=case.as_of - timedelta(minutes=5),
        valid_at=case.starts_at + timedelta(minutes=30 * index),
        max_age_seconds=3600, lower_bound=8.0, upper_bound=12.0,
    ) for index in range(48)]


def test_missing_checked_source_returns_incomplete_preview(monkeypatch, tmp_path):
    source = load_checked_constraint(datetime.now(UTC), tmp_path / "missing.json")
    assert source.status == "unavailable" and source.values == []
    monkeypatch.setattr(decision_routes, "load_checked_constraint", lambda _as_of: source)
    response = client.post("/v1/decision/preview", json={"case": case_payload()})
    assert response.status_code == 200
    body = response.json()
    assert body["contract_status"] == "pending_review"
    assert body["recommendation"] is None
    assert body["current_plan"]["expected_dispatch_down_mwh"] is None
    assert len(body["current_plan"]["intervals"]) == 48
    assert body["evidence_coverage"]["constraint_mwh"]["missing_intervals"] == 48
    assert body["similar_cases"] == []
    assert body["scenario_intake"][0]["scenario_id"] == "T1"
    assert "normal_flow_mw" in body["scenario_intake"][0]["missing_fields"]
    assert body["scenario_intake"][0]["classification_verified"] is False
    assert any("Checked constraint snapshot unavailable" in gap for gap in body["blocking_reasons"])


def test_checked_national_constraint_is_inapplicable_to_locked_scenario(monkeypatch):
    payload = case_payload()
    payload["location"] = None
    case = DecisionCase.model_validate(payload)
    source = EvidenceSourceResult(source="checked GFS national constraint", status="available",
                                  values=checked_rows(case))
    monkeypatch.setattr(decision_routes, "load_checked_constraint", lambda _as_of: source)
    response = client.post("/v1/decision/preview", json={
        "case": payload, "conditions": {"season": "autumn"},
        "include_modelled_demo_cases": True,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["status"] == "inapplicable"
    assert body["current_plan"]["expected_constraint_mwh"] is None
    assert body["evidence_coverage"]["constraint_mwh"]["available_intervals"] == 0
    assert body["evidence_coverage"]["curtailment_mwh"]["missing_intervals"] == 48
    assert body["current_plan"]["expected_curtailment_mwh"] is None
    assert body["current_plan"]["expected_dispatch_down_mwh"] is None
    assert body["current_plan"]["safety"]["safety_gate_passed"] is False
    assert body["recommendation"] is None
    assert body["similar_cases"] == []  # Legacy synthetic cases have no justified T1 mapping.


def test_national_constraint_does_not_populate_locational_baseline(monkeypatch):
    payload = case_payload()
    case = DecisionCase.model_validate(payload)
    source = EvidenceSourceResult(source="checked GFS national constraint", status="available",
                                  values=checked_rows(case))
    monkeypatch.setattr(decision_routes, "load_checked_constraint", lambda _as_of: source)
    response = client.post("/v1/decision/preview", json={"case": payload})
    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["status"] == "inapplicable"
    assert body["current_plan"]["expected_constraint_mwh"] is None
    assert body["evidence_coverage"]["constraint_mwh"]["missing_intervals"] == 48
    assert any("Experimental national constraint total cannot establish" in gap for gap in body["blocking_reasons"])


def test_preview_rejects_client_forecast_fields(monkeypatch):
    payload = case_payload()
    response = client.post("/v1/decision/preview", json={
        "case": payload, "evidence": [{"field": "constraint_mwh", "value": 1000}],
    })
    assert response.status_code == 422


def test_contract_manifest_keeps_jack_decisions_pending():
    manifest = load_contract_manifest()
    case = DecisionCase.model_validate(case_payload())
    assert manifest.status == "pending_review"
    assert set(manifest.scenario_ids) == SCENARIO_IDS
    assert manifest.scenario_catalogue_reference.endswith("/issues/47")
    assert required_case_facts(manifest, case) == set()
    assert contract_gaps(manifest, case) == [
        "Action, required-fact, and outcome-metric contracts are pending domain review"
    ]
    with pytest.raises(ValidationError, match="approved contract needs"):
        DecisionContractManifest(
            status="approved", approval_reference=None, scenario_ids=[], action_ids=[],
            required_facts_by_scenario={}, outcome_metrics_approved=False,
        )
    with pytest.raises(ValidationError, match="approved contract needs"):
        DecisionContractManifest(
            status="approved", approval_reference="review-v1",
            scenario_ids=["local_constraint"], action_ids=["reviewed-action"],
            required_facts_by_scenario={"local_constraint": []},
            outcome_metrics_approved=True,
        )


def test_approved_fact_specs_enforce_unit_source_and_interval_coverage():
    case = DecisionCase.model_validate(case_payload())
    manifest = DecisionContractManifest(
        status="approved", approval_reference="reviewed-scenario-contract-v1",
        scenario_catalogue_reference="https://github.com/Ishaan005/hacktheclimate/issues/47",
        scenario_ids=["T1"], action_ids=["reviewed-action"],
        required_facts_by_scenario={"T1": [{
            "field": "demand_mw", "unit": "MW", "allowed_source_types": ["forecast"],
            "cadence": "half_hour", "max_age_seconds": 3600,
        }]}, outcome_metrics_approved=True,
    )
    assert required_case_facts(manifest, case) == {"demand_mw"}
    one_wrong_unit = EvidenceValue(
        field="demand_mw", value=100.0, unit="MWh", source_type="forecast",
        source="reviewed-test", source_version="v1",
        available_at=case.as_of - timedelta(minutes=1),
        issued_at=case.as_of - timedelta(minutes=5), valid_at=case.starts_at,
        max_age_seconds=3600,
    )
    context = resolve_case_context(case, [one_wrong_unit], required_fields=["demand_mw"])
    assert fact_gaps(manifest, context) == [
        "T1: required demand_mw covers 0/48 half-hours with approved units and sources"
    ]
    corrected = [one_wrong_unit.model_copy(update={
        "unit": "MW", "valid_at": case.starts_at + timedelta(minutes=30 * index),
    }) for index in range(48)]
    context = resolve_case_context(case, corrected, required_fields=["demand_mw"])
    assert fact_gaps(manifest, context) == []


def test_partial_scoped_evidence_reports_interval_gap():
    payload = case_payload()
    payload["location"] = None
    case = DecisionCase.model_validate(payload)
    source = EvidenceSourceResult(source="reviewed-scoped-test", status="available",
                                  values=checked_rows(case)[:12])
    result = evaluate_case(
        case, evidence=source.values, sources=[source],
        manifest=load_contract_manifest(), policy=load_demo_policy(),
    )
    assert result.evidence_coverage["constraint_mwh"].available_intervals == 12
    assert result.current_plan.expected_constraint_mwh is None
    assert "constraint_mwh covers 12/48 future intervals" in result.blocking_reasons


def test_locked_scenario_catalogue_and_multi_label_intake():
    catalogue = load_scenario_catalogue()
    assert {item.scenario_id for item in catalogue.definitions} == SCENARIO_IDS
    assert len([item for item in catalogue.definitions if item.family == "transmission"]) == 4
    assert all(len(item.variants) == 3 for item in catalogue.definitions if item.family == "transmission")
    assert "measured_frequency_hz" in next(item for item in catalogue.definitions if item.scenario_id == "H1").intake_fields
    response = client.get("/v1/decision/scenarios")
    assert response.status_code == 200
    assert response.json()["source"] == catalogue.source

    payload = case_payload()
    payload["scenario_ids"] = ["T3", "SNSP"]
    case = DecisionCase.model_validate(payload)
    assert contract_gaps(load_contract_manifest(), case) == [
        "Action, required-fact, and outcome-metric contracts are pending domain review"
    ]


def test_unknown_cause_is_intake_state_not_scenario(monkeypatch, tmp_path):
    payload = case_payload()
    payload["scenario_ids"] = []
    payload["cause_unknown"] = True
    case = DecisionCase.model_validate(payload)
    assert "Limiting cause unknown" in contract_gaps(load_contract_manifest(), case)[0]
    source = load_checked_constraint(case.as_of, tmp_path / "missing.json")
    monkeypatch.setattr(decision_routes, "load_checked_constraint", lambda _as_of: source)
    body = client.post("/v1/decision/preview", json={"case": payload}).json()
    assert body["recommendation"] is None
    assert body["similar_cases"] == []
    assert any("Limiting cause unknown" in reason for reason in body["blocking_reasons"])
    with pytest.raises(ValidationError, match="cause-unknown"):
        DecisionCase.model_validate({**payload, "scenario_ids": ["T1"]})
    with pytest.raises(ValidationError, match="cause-unknown"):
        DecisionCase.model_validate({**payload, "cause_unknown": False})


def test_legacy_demo_label_is_not_mapped_to_locked_scenario():
    payload = case_payload()
    payload["scenario_ids"] = ["local_constraint"]
    case = DecisionCase.model_validate(payload)
    assert "Unknown scenario IDs: local_constraint" in contract_gaps(load_contract_manifest(), case)


def test_h1_requires_measured_frequency_even_if_forecast_value_exists():
    payload = case_payload()
    payload["scenario_ids"] = ["H1"]
    case = DecisionCase.model_validate(payload)
    forecast = EvidenceValue(
        field="measured_frequency_hz", value=50.2, unit="Hz", source_type="forecast",
        source="test forecast", source_version="v1", available_at=case.as_of - timedelta(minutes=1),
        issued_at=case.as_of - timedelta(minutes=2), valid_at=case.starts_at,
        max_age_seconds=3600,
    )
    context = resolve_case_context(case, [forecast])
    assessment = assess_scenario_intake(context, load_scenario_catalogue())[0]
    assert "measured_frequency_hz" in assessment.missing_fields
    assert not assessment.classification_verified
    measured = EvidenceValue(
        field="measured_frequency_hz", value=50.2, unit="Hz", source_type="measurement",
        source="test meter", source_version="v1", available_at=case.as_of - timedelta(minutes=1),
        observed_at=case.as_of - timedelta(minutes=2), max_age_seconds=3600,
    )
    context = resolve_case_context(case, [measured])
    assessment = assess_scenario_intake(context, load_scenario_catalogue())[0]
    assert "measured_frequency_hz" in assessment.recorded_fields
    assert not assessment.classification_verified

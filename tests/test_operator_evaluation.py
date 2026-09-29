from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from backend.app.decision import DecisionCase, EvidenceValue
from backend.app.network_scenarios import Asset
from backend.app.operator_evaluation import OperatorEvaluationRequest, evaluate_operator_case
from test_network_forecast import _case, _crosswalk, _rows
from test_action_bundles import _redispatch_candidate
from test_network_safety_actions import _candidate


def _request(*, evidence: bool = True, action_candidates=None) -> OperatorEvaluationRequest:
    rows = _rows()
    for row in rows:
        row["recoverable_renewable_mw"] = {"South-West": {"wind": 10.0}}
    as_of = datetime(2026, 9, 28, 23, 45, tzinfo=timezone.utc)
    start = datetime(2026, 9, 29, tzinfo=timezone.utc)
    values = []
    if evidence:
        for index in range(48):
            valid = start + timedelta(minutes=index * 30)
            for field, amount in (("constraint_mwh", 20.0), ("curtailment_mwh", 2.0)):
                values.append(EvidenceValue(
                    field=field, value=amount, unit="MWh per half-hour",
                    source_type="forecast", source="synthetic test forecast",
                    source_version="test-1", issued_at=as_of - timedelta(hours=1),
                    available_at=as_of - timedelta(minutes=5), valid_at=valid,
                    max_age_seconds=3600,
                ))
    return OperatorEvaluationRequest(
        decision_case=DecisionCase(
            case_id="synthetic-test", scenario_ids=["T1"], as_of=as_of,
            starts_at=start, ends_at=start + timedelta(hours=24),
        ),
        forecast_available_at=as_of - timedelta(minutes=5),
        forecast_version="synthetic-test-1",
        forecast_evidence_reference="synthetic unit test",
        forecast_rows=rows,
        action_candidates=[_candidate()] if action_candidates is None else action_candidates,
        evidence=values,
    )


def test_evaluation_joins_current_plan_network_effect_and_blocks_ranking():
    result = evaluate_operator_case(
        _request(), _case(), _crosswalk(), planned_outage=Asset("branch", "1:3:1"),
    )
    assert result["current_plan"]["expected_dispatch_down_mwh"] == pytest.approx(1056)
    assert len(result["forecast"]) == 48
    action = result["actions"][0]
    assert action["modeled_capture_upper_bound_mwh"] == pytest.approx(10)
    assert action["expected_avoided_constraint_mwh"] is None
    assert action["intervals"][0]["network_effect"]["planned_outage"]["base"] != action["intervals"][0]["network_effect"]["planned_outage"]["with_action"]
    assert action["contract_action_id"] == "FLEX_LOAD"
    assert "network_loading" in action["required_safety_rules"]
    assert action["required_safety_families"] == ["transmission"]
    flex_resolution = next(
        item for item in result["eligible_actions"] if item["action_id"] == "FLEX_LOAD"
    )
    assert flex_resolution["required_safety_families"] == ["transmission"]
    assert any(item["action_id"] == "NETWORK_SWITCHING" for item in result["unavailable_actions"])
    assert result["ranked_modeled_capture_bounds"][0]["action_id"] == action["action_id"]
    assert result["ranked_expected_avoided_dispatch_down"] == []
    assert result["recommendation"] is None
    assert not result["current_plan"]["safety"]["safety_gate_passed"]


def test_missing_energy_evidence_stays_missing():
    result = evaluate_operator_case(
        _request(evidence=False), _case(), _crosswalk(),
        planned_outage=Asset("branch", "1:3:1"),
    )
    assert result["current_plan"]["expected_dispatch_down_mwh"] is None
    assert result["current_plan"]["status"] == "incomplete"
    assert result["ranked_expected_avoided_dispatch_down"] == []


def test_mismatched_or_late_forecast_is_rejected():
    request = _request()
    payload = request.model_dump(mode="json")
    payload["forecast_rows"][0]["expected_constraint_mwh"] = 19.0
    with pytest.raises(ValueError, match="disagrees"):
        evaluate_operator_case(
            OperatorEvaluationRequest.model_validate(payload), _case(), _crosswalk(),
            planned_outage=Asset("branch", "1:3:1"),
        )
    payload = request.model_dump(mode="json")
    for row in payload["forecast_rows"]:
        row["issue_time"] = "2026-09-28T23:50:00Z"
    with pytest.raises(ValidationError, match="later than the request"):
        OperatorEvaluationRequest.model_validate(payload)


def test_evaluation_includes_baseline_and_shared_budget_bundles():
    second = _candidate().copy()
    second["action_id"] = "illustrative-flex-2"
    result = evaluate_operator_case(
        _request(action_candidates=[_candidate(), second]),
        _case(), _crosswalk(), planned_outage=Asset("branch", "1:3:1"),
    )
    assert result["baseline_bundle"]["bundle_id"] == "BASELINE"
    assert result["baseline_bundle"]["modeled_capture_upper_bound_mwh"] == 0
    assert result["baseline_bundle"]["expected_dispatch_down_mwh"] == pytest.approx(1056)

    pair = next(
        bundle for bundle in result["bundle_options"]
        if len(bundle["action_instance_ids"]) == 2
    )
    assert pair["modeled_capture_upper_bound_mwh"] == pytest.approx(10.0)
    assert pair["expected_avoided_dispatch_down_mwh"] is None
    assert pair["missing_required_safety_rules"] == []
    assert pair["required_safety_families"] == ["transmission"]
    assert pair["missing_required_safety_families"] == []
    assert pair["action_specific"]["asset_capability"]["status"] == "UNKNOWN"
    assert pair["action_specific"]["timing"]["status"] == "UNKNOWN"
    # A modeled breach wins over unresolved contract checks: FAIL must not be
    # softened to UNKNOWN just because asset capability/timing are also missing.
    assert pair["safety_overall"] == "FAIL"
    assert result["best_screening_pass_bundle"] is None
    assert result["recommendation"] is None



def test_complete_action_evidence_resolves_asset_and_timing_contract_rules():
    candidate = _candidate()
    candidate["operational_evidence"] = {
        "named_asset_or_party": "Flexible demand site A",
        "authority_status": "confirmed",
        "permission_status": "confirmed",
        "availability_status": "available",
        "response_time_minutes": 10.0,
        "sustain_duration_minutes": 60.0,
        "capability_mw": 10.0,
        "side_effects_review_status": "reviewed",
        "evidence_reference": "synthetic operator evidence",
        "available_at": "2026-09-28T23:40:00Z",
        "max_age_seconds": 3600,
        "valid_until": "2026-09-29T01:00:00Z",
    }
    result = evaluate_operator_case(
        _request(action_candidates=[candidate]),
        _case(), _crosswalk(), planned_outage=Asset("branch", "1:3:1"),
    )

    bundle = next(
        item for item in result["bundle_options"]
        if item["action_instance_ids"] == ["illustrative-flex-1"]
    )
    assert bundle["action_specific"]["asset_capability"]["status"] == "PASS"
    assert bundle["action_specific"]["timing"]["status"] == "PASS"
    assert "asset_capability" not in bundle["missing_required_safety_rules"]
    assert "timing" not in bundle["missing_required_safety_rules"]


def test_no_action_candidates_leaves_baseline_as_only_bundle_option():
    result = evaluate_operator_case(
        _request(action_candidates=[]),
        _case(), _crosswalk(), planned_outage=Asset("branch", "1:3:1"),
    )
    assert [bundle["bundle_id"] for bundle in result["bundle_options"]] == ["BASELINE"]
    assert result["best_modeled_capture_bundle"] == "BASELINE"
    assert result["best_screening_pass_bundle"] is None
    assert any("No scenario-valid planning-supported action candidates" in reason
               for reason in result["blocking_reasons"])


def test_operator_evaluation_exposes_redispatch_and_mixed_bundle():
    flex = _candidate()
    redispatch = _redispatch_candidate()
    result = evaluate_operator_case(
        _request(action_candidates=[flex, redispatch]),
        _case(), _crosswalk(), planned_outage=Asset("branch", "1:3:1"),
    )

    eligible = {item["action_id"]: item for item in result["eligible_actions"]}
    assert eligible["GENERATOR_REDISPATCH"]["execution_status"] == "planning_supported"
    assert not any(
        item["action_id"] == "GENERATOR_REDISPATCH"
        for item in result["unavailable_actions"]
    )

    redispatch_eval = next(
        item for item in result["planning_action_evaluations"]
        if item["action_instance_ids"] == ["redispatch-1"]
    )
    assert redispatch_eval["modeled_capture_upper_bound_mwh"] == pytest.approx(0.0)
    assert "reserve" in redispatch_eval["required_safety_rules"]
    assert "reserve" in redispatch_eval["missing_required_safety_rules"]

    mixed = next(
        item for item in result["bundle_options"]
        if set(item["action_instance_ids"]) == {"illustrative-flex-1", "redispatch-1"}
    )
    assert set(mixed["contract_action_ids"]) == {"FLEX_LOAD", "GENERATOR_REDISPATCH"}
    assert mixed["modeled_capture_upper_bound_mwh"] == pytest.approx(10.0)
    assert mixed["expected_avoided_dispatch_down_mwh"] is None
    assert result["recommendation"] is None

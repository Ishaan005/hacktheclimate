from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from backend.app.decision import DecisionCase, EvidenceValue
from backend.app.network_scenarios import Asset
from backend.app.operator_evaluation import OperatorEvaluationRequest, evaluate_operator_case
from test_network_forecast import _case, _crosswalk, _rows
from test_network_safety_actions import _candidate


def _request(*, evidence: bool = True) -> OperatorEvaluationRequest:
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
            case_id="synthetic-test", scenario_ids=["local_constraint"], as_of=as_of,
            starts_at=start, ends_at=start + timedelta(hours=24),
        ),
        forecast_available_at=as_of - timedelta(minutes=5),
        forecast_version="synthetic-test-1",
        forecast_evidence_reference="synthetic unit test",
        forecast_rows=rows, action_candidates=[_candidate()], evidence=values,
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

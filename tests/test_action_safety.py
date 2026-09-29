from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from backend.app.decision import (
    DecisionCase,
    evaluate_action_bundle_operational_safety,
    evaluate_action_operational_safety,
)
from test_network_safety_actions import _candidate


def _case() -> DecisionCase:
    start = datetime(2026, 9, 29, tzinfo=timezone.utc)
    return DecisionCase(
        case_id="action-safety-test",
        scenario_ids=["T1"],
        as_of=start - timedelta(minutes=15),
        starts_at=start,
        ends_at=start + timedelta(hours=24),
    )


def _evidenced_candidate() -> dict:
    candidate = deepcopy(_candidate())
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
    return candidate


def test_complete_action_operational_evidence_passes_both_contract_gates():
    result = evaluate_action_operational_safety(_evidenced_candidate(), _case())

    assert result.asset_capability.status == "PASS"
    assert result.timing.status == "PASS"
    assert result.overall == "PASS"
    assert result.checks["capability"].status == "PASS"
    assert result.checks["response_time"].status == "PASS"


def test_missing_operational_evidence_stays_unknown():
    result = evaluate_action_operational_safety(_candidate(), _case())

    assert result.asset_capability.status == "UNKNOWN"
    assert result.timing.status == "UNKNOWN"
    assert result.overall == "UNKNOWN"


def test_capability_shortfall_is_a_fail():
    candidate = _evidenced_candidate()
    candidate["operational_evidence"]["capability_mw"] = 5.0

    result = evaluate_action_operational_safety(candidate, _case())

    assert result.checks["capability"].status == "FAIL"
    assert result.asset_capability.status == "FAIL"
    assert result.overall == "FAIL"


def test_response_after_first_target_interval_is_a_fail():
    candidate = _evidenced_candidate()
    candidate["operational_evidence"]["response_time_minutes"] = 30.0

    result = evaluate_action_operational_safety(candidate, _case())

    assert result.checks["response_time"].status == "FAIL"
    assert result.timing.status == "FAIL"
    assert result.overall == "FAIL"


def test_bundle_requires_every_action_to_pass_operational_gates():
    first = _evidenced_candidate()
    second = _evidenced_candidate()
    second["action_id"] = "illustrative-flex-2"
    second["operational_evidence"]["named_asset_or_party"] = "Flexible demand site B"
    second["operational_evidence"]["permission_status"] = "denied"

    result = evaluate_action_bundle_operational_safety([first, second], _case())

    assert result.asset_capability.status == "PASS"
    assert result.timing.status == "FAIL"
    assert result.overall == "FAIL"
    # Permission failure blocks execution, but physical response timing itself
    # is still fast enough for the transmission time-to-relief check.
    assert result.relief_timing_verified is True


def test_stale_operational_evidence_becomes_unknown():
    candidate = _evidenced_candidate()
    candidate["operational_evidence"]["available_at"] = "2026-09-28T22:00:00Z"
    candidate["operational_evidence"]["max_age_seconds"] = 60

    result = evaluate_action_operational_safety(candidate, _case())

    assert result.asset_capability.status == "UNKNOWN"
    assert result.timing.status == "UNKNOWN"
    assert result.overall == "UNKNOWN"

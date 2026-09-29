from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from backend.app.decision import (
    DecisionCase, EvidenceValue, ExistingInstruction, PastCase, append_case,
    best_case_metrics, calculate_current_plan, evaluate_policy, load_cases,
    load_demo_policy, resolve_case_context, search_cases,
)
from backend.app.decision.policy import SafetyPolicy
from backend.app.decision.contracts import SourceReference
from backend.app.safety import CheckResult, SafetyResult

UTC = timezone.utc
AS_OF = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)
START = AS_OF + timedelta(minutes=30)


def make_case(*, instructions=None) -> DecisionCase:
    return DecisionCase(
        case_id="case-1", scenario_ids=["local_constraint"], location="illustrative-west",
        asset_ids=["illustrative-asset"], as_of=AS_OF,
        starts_at=START, ends_at=START + timedelta(hours=24),
        existing_instructions=instructions or [],
    )


def energy(field: str, time: datetime, value: float | None, *, available_at=AS_OF - timedelta(minutes=5),
           lower_bound=None, upper_bound=None, max_age_seconds=3600) -> EvidenceValue:
    return EvidenceValue(
        field=field, value=value, unit="MWh per half-hour", source_type="forecast",
        source="reviewed-test-forecast", source_version="version-1",
        available_at=available_at, issued_at=AS_OF - timedelta(minutes=10),
        valid_at=time, max_age_seconds=max_age_seconds,
        lower_bound=lower_bound, upper_bound=upper_bound,
    )


def full_energy(*, include_curtailment=True):
    values = []
    for index in range(48):
        time = START + timedelta(minutes=30 * index)
        values.append(energy("constraint_mwh", time, 10.0, lower_bound=8.0, upper_bound=12.0))
        if include_curtailment:
            values.append(energy("curtailment_mwh", time, 5.0, lower_bound=4.0, upper_bound=6.0))
    return values


def planning_result(*, thermal="PASS", islanding="PASS") -> SafetyResult:
    unknown = CheckResult("UNKNOWN", "not evaluated")
    return SafetyResult(
        overall="FAIL" if thermal == "FAIL" or islanding == "FAIL" else "UNKNOWN",
        thermal=CheckResult(thermal, "TYTFS DC proxy", "test-case"),
        islanding=CheckResult(islanding, "TYTFS topology", "test-case"),
        snsp=unknown, voltage=unknown, inertia=unknown, rocof=unknown,
    )


def test_decision_time_rejects_late_values_and_marks_stale_or_missing():
    case = make_case()
    with pytest.raises(ValueError, match="unavailable"):
        resolve_case_context(case, [energy("constraint_mwh", START, 10.0, available_at=AS_OF + timedelta(seconds=1))])
    old = energy("constraint_mwh", START, 10.0, max_age_seconds=10)
    context = resolve_case_context(case, [old, energy("curtailment_mwh", START, None)],
                                   required_fields=["constraint_mwh", "curtailment_mwh"])
    assert context.values["constraint_mwh"][0].status == "stale"
    assert context.values["curtailment_mwh"][0].status == "missing"
    assert context.missing_fields == ["constraint_mwh", "curtailment_mwh"]


def test_policy_registry_covers_roadmap_and_breach_precedes_unknown():
    policy = load_demo_policy()
    assert {rule.rule_id for rule in policy.rules} >= {"reserve", "system_strength", "minimum_online_units", "timing"}
    with pytest.raises(ValidationError, match="missing required rules"):
        SafetyPolicy(policy_id="broken", version="1", rules=policy.rules[:-1])
    context = resolve_case_context(make_case(), full_energy())
    times = [START + timedelta(minutes=30 * index) for index in range(48)]
    screens = {time: planning_result(thermal="FAIL" if index == 4 else "PASS")
               for index, time in enumerate(times)}
    result = evaluate_policy(policy, context, planning_safety=screens)
    assert result.overall == "BREACH"
    assert not result.safety_gate_passed
    assert next(rule for rule in result.rules if rule.rule_id == "network_loading").status == "BREACH"
    assert next(rule for rule in result.rules if rule.rule_id == "reserve").status == "UNKNOWN"


def test_current_plan_applies_only_unreflected_instructions_and_keeps_components_separate():
    instruction = ExistingInstruction(
        instruction_id="already-in-force", starts_at=START, ends_at=START + timedelta(hours=1),
        evidence_reference="operator-confirmed-instruction", included_in_forecast=False,
        constraint_delta_mwh_per_interval=-2.0, curtailment_delta_mwh_per_interval=0.0,
    )
    context = resolve_case_context(make_case(instructions=[instruction]), full_energy())
    result = calculate_current_plan(context, load_demo_policy())
    assert len(result.intervals) == 48
    assert result.intervals[0].constraint_mwh == 8.0
    assert result.intervals[0].curtailment_mwh == 5.0
    assert result.intervals[2].constraint_mwh == 10.0
    assert result.expected_constraint_mwh == 476.0
    assert result.expected_curtailment_mwh == 240.0
    assert result.expected_dispatch_down_mwh == 716.0
    assert result.dispatch_down_lower_mwh == 572.0
    assert result.dispatch_down_upper_mwh == 860.0
    assert result.safety.overall == "UNKNOWN"
    assert result.source_versions == ["version-1"]


def test_best_case_is_bounded_and_never_becomes_expected_or_safe():
    context = resolve_case_context(make_case(), full_energy())
    baseline = calculate_current_plan(context, load_demo_policy())
    optimistic = best_case_metrics(baseline, action_power_mw=10.0, duration_hours=2.0,
                                   verified_recoverable_mwh=7.0)
    assert optimistic.avoided_constraint_upper_mwh == 7.0
    assert optimistic.avoided_dispatch_down_upper_mwh == 7.0
    assert optimistic.incremental_cost_assumption == 0.0
    assert not optimistic.recommendation_allowed
    assert baseline.expected_constraint_mwh == 480.0
    with pytest.raises(ValueError, match="duration"):
        best_case_metrics(baseline, action_power_mw=10.0, duration_hours=25.0)


def test_case_library_is_append_only_and_separates_observed_from_modelled(tmp_path):
    records = load_cases()
    assert len(records) >= 2 and all(item.outcome_label == "modelled" for item in records)
    modelled = records[0]
    with pytest.raises(ValidationError, match="measured case-level evidence"):
        PastCase.model_validate({**modelled.model_dump(), "outcome_label": "observed"})
    observed = modelled.model_copy(update={
        "record_id": "real-case-1", "outcome_label": "observed", "quality": "high",
        "sources": [SourceReference(reference="case-level meter and action log", kind="measured")],
    })
    path = tmp_path / "cases.jsonl"
    append_case(path, observed)
    with pytest.raises(ValueError, match="already exists"):
        append_case(path, observed)
    found = search_cases([*records, *load_cases(path)], make_case(),
                         conditions={"demand_mw": 2100.0}, minimum_quality="low")
    assert found[0].record.record_id == "real-case-1"
    assert "observed" in found[0].reason
    assert any(item.record.outcome_label == "modelled" for item in found)


def test_incomplete_case_integrates_evidence_baseline_lookup_and_safety():
    case = make_case()
    context = resolve_case_context(case, full_energy(include_curtailment=False),
                                   required_fields=["constraint_mwh", "curtailment_mwh"])
    baseline = calculate_current_plan(context, load_demo_policy())
    similar = search_cases(load_cases(), case, conditions={"season": "autumn"})
    optimistic = best_case_metrics(baseline, action_power_mw=5.0, duration_hours=1.0)
    assert context.missing_fields == ["curtailment_mwh"]
    assert baseline.expected_constraint_mwh == 480.0
    assert baseline.expected_dispatch_down_mwh is None
    assert optimistic.avoided_constraint_upper_mwh == 5.0
    assert optimistic.avoided_dispatch_down_upper_mwh is None
    assert baseline.safety.overall == "UNKNOWN" and not baseline.safety.safety_gate_passed
    assert similar and all(item.record.outcome_label == "modelled" for item in similar)

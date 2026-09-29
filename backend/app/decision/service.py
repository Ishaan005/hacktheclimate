"""One case flow for the independent Ishaan workstreams."""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.app.safety import SafetyResult

from .baseline import BaselineResult, OptimisticMetrics, best_case_metrics, calculate_current_plan
from .cases import ComparableCase, search_cases
from .contracts import Contract, DecisionCase, EvidenceValue, PastCase, ResolvedContext, utc
from .evidence import resolve_case_context
from .manifest import DecisionContractManifest, contract_gaps, fact_gaps, required_case_facts
from .policy import SafetyPolicy
from .sources import EvidenceSourceResult


class IllustrativeAction(Contract):
    power_mw: float | None = None
    duration_hours: float | None = None
    verified_recoverable_mwh: float | None = None
    incremental_cost: float | None = None


class EvidenceCoverage(Contract):
    expected_intervals: int
    available_intervals: int
    stale_intervals: int
    missing_intervals: int


class CaseEvaluation(Contract):
    case: DecisionCase
    contract_status: str
    sources: list[EvidenceSourceResult]
    context: ResolvedContext
    evidence_coverage: dict[str, EvidenceCoverage]
    current_plan: BaselineResult
    similar_cases: list[ComparableCase]
    optimistic_scenario: OptimisticMetrics | None
    blocking_reasons: list[str]
    recommendation: None = None


def _coverage(context: ResolvedContext, fields: set[str]) -> dict[str, EvidenceCoverage]:
    times = {utc(context.case.starts_at) + timedelta(minutes=30 * index) for index in range(48)}
    output = {}
    for field in sorted(fields):
        by_time = {
            utc(item.evidence.valid_at): item.status
            for item in context.values.get(field, [])
            if item.evidence.valid_at is not None and utc(item.evidence.valid_at) in times
        }
        available = sum(status == "available" for status in by_time.values())
        stale = sum(status == "stale" for status in by_time.values())
        output[field] = EvidenceCoverage(
            expected_intervals=48, available_intervals=available, stale_intervals=stale,
            missing_intervals=48 - available - stale,
        )
    return output


def evaluate_case(
    case: DecisionCase,
    *,
    evidence: list[EvidenceValue],
    sources: list[EvidenceSourceResult],
    manifest: DecisionContractManifest,
    policy: SafetyPolicy,
    past_cases: list[PastCase] | None = None,
    conditions: dict[str, float | str] | None = None,
    illustrative_action: IllustrativeAction | None = None,
    planning_safety: dict[datetime, SafetyResult] | None = None,
) -> CaseEvaluation:
    """Resolve known inputs and return reasons instead of an invented decision."""
    required = {"constraint_mwh", "curtailment_mwh", *required_case_facts(manifest, case)}
    context = resolve_case_context(case, evidence, required_fields=required)
    coverage = _coverage(context, {"constraint_mwh", "curtailment_mwh"})
    baseline = calculate_current_plan(context, policy, planning_safety=planning_safety)
    similar = search_cases(past_cases or [], case, conditions=conditions)
    optimistic = (
        best_case_metrics(
            baseline, action_power_mw=illustrative_action.power_mw,
            duration_hours=illustrative_action.duration_hours,
            verified_recoverable_mwh=illustrative_action.verified_recoverable_mwh,
            incremental_cost=illustrative_action.incremental_cost,
        ) if illustrative_action else None
    )
    blockers = contract_gaps(manifest, case)
    blockers.extend(fact_gaps(manifest, context))
    if case.existing_instructions:
        blockers.append("Existing instruction effects need source review before operational use")
    blockers.extend(f"Required field unavailable or stale: {field}" for field in context.missing_fields)
    blockers.extend(
        f"{field} covers {item.available_intervals}/48 future intervals"
        for field, item in coverage.items() if item.available_intervals < 48
    )
    blockers.extend(f"{source.source}: {source.reason}" for source in sources if source.status != "available")
    if baseline.expected_dispatch_down_mwh is None:
        blockers.append("Current-plan total dispatch-down MWh is unavailable")
    if not baseline.safety.safety_gate_passed:
        blockers.append(f"Current-plan safety policy {baseline.safety.overall.lower()}")
    return CaseEvaluation(
        case=case, contract_status=manifest.status, sources=sources, context=context,
        evidence_coverage=coverage,
        current_plan=baseline, similar_cases=similar,
        optimistic_scenario=optimistic, blocking_reasons=list(dict.fromkeys(blockers)),
    )

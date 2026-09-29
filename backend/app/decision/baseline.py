"""Current-plan outcome and separately labelled optimistic action bounds."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import isfinite
from typing import Literal

from pydantic import Field

from .contracts import Contract, DecisionCase, ResolvedContext, ResolvedValue, utc
from .policy import PolicyResult, SafetyPolicy, evaluate_policy


class IntervalOutcome(Contract):
    valid_at: datetime
    constraint_mwh: float | None
    curtailment_mwh: float | None
    dispatch_down_mwh: float | None
    constraint_lower_mwh: float | None
    constraint_upper_mwh: float | None
    curtailment_lower_mwh: float | None
    curtailment_upper_mwh: float | None
    dispatch_down_lower_mwh: float | None
    dispatch_down_upper_mwh: float | None
    missing: list[str]


class BaselineResult(Contract):
    case_id: str
    starts_at: datetime
    ends_at: datetime
    intervals: list[IntervalOutcome] = Field(min_length=48, max_length=48)
    expected_constraint_mwh: float | None
    expected_curtailment_mwh: float | None
    expected_dispatch_down_mwh: float | None
    constraint_lower_mwh: float | None
    constraint_upper_mwh: float | None
    curtailment_lower_mwh: float | None
    curtailment_upper_mwh: float | None
    dispatch_down_lower_mwh: float | None
    dispatch_down_upper_mwh: float | None
    existing_instruction_ids: list[str]
    source_versions: list[str]
    missing_data: list[str]
    safety: PolicyResult
    status: Literal["metrics_complete", "incomplete"]


class OptimisticMetrics(Contract):
    label: str = "illustrative optimistic scenario; not expected or verified savings"
    avoided_constraint_upper_mwh: float | None
    avoided_dispatch_down_upper_mwh: float | None
    incremental_cost_assumption: float | None
    assumptions: list[str]
    recommendation_allowed: bool = False


def _at(context: ResolvedContext, field: str, time: datetime) -> ResolvedValue | None:
    return next((item for item in context.values.get(field, [])
                 if item.evidence.valid_at is not None and utc(item.evidence.valid_at) == time), None)


def _component(context: ResolvedContext, field: str, time: datetime) -> tuple[float | None, float | None, float | None, str | None]:
    item = _at(context, field, time)
    if item is None or item.status != "available":
        return None, None, None, f"{field} at {time.isoformat()}: {item.status if item else 'missing'}"
    if item.evidence.unit != "MWh per half-hour" or not isinstance(item.evidence.value, (int, float)) or isinstance(item.evidence.value, bool):
        return None, None, None, f"{field} at {time.isoformat()}: wrong unit or value type"
    value = float(item.evidence.value)
    if not isfinite(value) or value < 0:
        return None, None, None, f"{field} at {time.isoformat()}: invalid energy value"
    lower = item.evidence.lower_bound if item.evidence.lower_bound is not None else value
    upper = item.evidence.upper_bound if item.evidence.upper_bound is not None else value
    return value, lower, upper, None


def _sum_complete(values: list[float | None]) -> float | None:
    return sum(value for value in values if value is not None) if all(value is not None for value in values) else None


def calculate_current_plan(
    context: ResolvedContext,
    policy: SafetyPolicy,
    *,
    planning_safety: dict | None = None,
) -> BaselineResult:
    """Apply only quantified instructions not already included in source forecasts."""
    case: DecisionCase = context.case
    rows: list[IntervalOutcome] = []
    missing: list[str] = []
    for index in range(48):
        time = utc(case.starts_at) + timedelta(minutes=30 * index)
        constraint, constraint_lower, constraint_upper, constraint_gap = _component(context, "constraint_mwh", time)
        curtailment, curtailment_lower, curtailment_upper, curtailment_gap = _component(context, "curtailment_mwh", time)
        gaps = [gap for gap in (constraint_gap, curtailment_gap) if gap]
        for instruction in case.existing_instructions:
            if instruction.included_in_forecast or not utc(instruction.starts_at) <= time < utc(instruction.ends_at):
                continue
            for name, delta in (
                ("constraint", instruction.constraint_delta_mwh_per_interval),
                ("curtailment", instruction.curtailment_delta_mwh_per_interval),
            ):
                if delta is None:
                    gaps.append(f"{instruction.instruction_id}: {name} effect unknown at {time.isoformat()}")
                    if name == "constraint":
                        constraint = constraint_lower = constraint_upper = None
                    else:
                        curtailment = curtailment_lower = curtailment_upper = None
                elif name == "constraint" and constraint is not None:
                    constraint = max(0.0, constraint + delta)
                    constraint_lower = max(0.0, constraint_lower + delta) if constraint_lower is not None else None
                    constraint_upper = max(0.0, constraint_upper + delta) if constraint_upper is not None else None
                elif name == "curtailment" and curtailment is not None:
                    curtailment = max(0.0, curtailment + delta)
                    curtailment_lower = max(0.0, curtailment_lower + delta) if curtailment_lower is not None else None
                    curtailment_upper = max(0.0, curtailment_upper + delta) if curtailment_upper is not None else None
        total = constraint + curtailment if constraint is not None and curtailment is not None else None
        total_lower = constraint_lower + curtailment_lower if constraint_lower is not None and curtailment_lower is not None else None
        total_upper = constraint_upper + curtailment_upper if constraint_upper is not None and curtailment_upper is not None else None
        rows.append(IntervalOutcome(
            valid_at=time, constraint_mwh=constraint, curtailment_mwh=curtailment,
            dispatch_down_mwh=total, constraint_lower_mwh=constraint_lower,
            constraint_upper_mwh=constraint_upper, curtailment_lower_mwh=curtailment_lower,
            curtailment_upper_mwh=curtailment_upper, dispatch_down_lower_mwh=total_lower,
            dispatch_down_upper_mwh=total_upper, missing=gaps,
        ))
        missing.extend(gaps)
    versions = sorted({item.evidence.source_version for group in context.values.values() for item in group if item.status == "available"})
    safety = evaluate_policy(policy, context, planning_safety=planning_safety)
    expected_constraint = _sum_complete([row.constraint_mwh for row in rows])
    expected_curtailment = _sum_complete([row.curtailment_mwh for row in rows])
    expected_total = _sum_complete([row.dispatch_down_mwh for row in rows])
    return BaselineResult(
        case_id=case.case_id, starts_at=case.starts_at, ends_at=case.ends_at,
        intervals=rows, expected_constraint_mwh=expected_constraint,
        expected_curtailment_mwh=expected_curtailment,
        expected_dispatch_down_mwh=expected_total,
        constraint_lower_mwh=_sum_complete([row.constraint_lower_mwh for row in rows]),
        constraint_upper_mwh=_sum_complete([row.constraint_upper_mwh for row in rows]),
        curtailment_lower_mwh=_sum_complete([row.curtailment_lower_mwh for row in rows]),
        curtailment_upper_mwh=_sum_complete([row.curtailment_upper_mwh for row in rows]),
        dispatch_down_lower_mwh=_sum_complete([row.dispatch_down_lower_mwh for row in rows]),
        dispatch_down_upper_mwh=_sum_complete([row.dispatch_down_upper_mwh for row in rows]),
        existing_instruction_ids=[item.instruction_id for item in case.existing_instructions],
        source_versions=versions, missing_data=missing, safety=safety,
        status="metrics_complete" if expected_total is not None else "incomplete",
    )


def best_case_metrics(
    baseline: BaselineResult,
    *,
    action_power_mw: float | None,
    duration_hours: float | None,
    verified_recoverable_mwh: float | None = None,
    incremental_cost: float | None = None,
) -> OptimisticMetrics:
    """Bound a demo upside without putting an estimate into the expected fields."""
    for name, value in (("action power", action_power_mw), ("duration", duration_hours),
                        ("recoverable energy", verified_recoverable_mwh), ("incremental cost", incremental_cost)):
        if value is not None and (not isfinite(value) or value < 0):
            raise ValueError(f"{name} must be finite and nonnegative")
    if duration_hours is not None and duration_hours > 24:
        raise ValueError("duration cannot exceed the 24-hour case window")
    capacity = action_power_mw * duration_hours if action_power_mw is not None and duration_hours is not None else None
    if capacity is not None and verified_recoverable_mwh is not None:
        capacity = min(capacity, verified_recoverable_mwh)
    constraint = min(capacity, baseline.constraint_upper_mwh) if capacity is not None and baseline.constraint_upper_mwh is not None else None
    total = min(capacity, baseline.dispatch_down_upper_mwh) if capacity is not None and baseline.dispatch_down_upper_mwh is not None else None
    assumptions = ["Action achieves the maximum bounded recoverable energy."] if capacity is not None else ["No finite action-capacity bound is available."]
    if verified_recoverable_mwh is None:
        assumptions.append("Local recoverable energy is unverified; no local cap was applied.")
    if incremental_cost is None:
        assumptions.append("Unknown incremental cost is shown as zero for this optimistic scenario only.")
    return OptimisticMetrics(
        avoided_constraint_upper_mwh=constraint,
        avoided_dispatch_down_upper_mwh=total,
        incremental_cost_assumption=incremental_cost if incremental_cost is not None else 0.0,
        assumptions=assumptions,
    )

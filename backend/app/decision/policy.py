"""Versioned demo safety rules; unknown evidence cannot become a pass."""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
from math import isfinite
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from backend.app.safety import SafetyResult

from .contracts import Contract, ResolvedContext, utc

POLICY_PATH = Path(__file__).resolve().parents[3] / "config/demo_safety_policy_v1.json"
REQUIRED_RULES = {
    "network_loading", "islanding", "voltage", "renewable_share", "inertia",
    "minimum_online_units", "rocof", "frequency", "reserve", "system_strength",
    "asset_capability", "timing",
}


class PolicyRule(Contract):
    rule_id: str
    applies_to: list[str] = Field(min_length=1)
    required_inputs: list[str] = Field(min_length=1)
    calculation: Literal["planning_dc", "max_le", "min_ge", "unavailable"]
    limit: float | None
    unit: str
    source: str
    approved: bool

    @model_validator(mode="after")
    def valid_rule(self):
        if self.approved and (self.limit is None or self.calculation == "unavailable" or not self.source.strip()):
            raise ValueError("approved rule needs a calculation, limit, and source")
        if self.limit is not None and not isfinite(self.limit):
            raise ValueError("policy limit must be finite")
        if self.calculation == "planning_dc" and self.rule_id not in {"network_loading", "islanding"}:
            raise ValueError("only network loading and islanding can use the planning DC screen")
        return self


class SafetyPolicy(Contract):
    policy_id: str
    version: str
    rules: list[PolicyRule]

    @model_validator(mode="after")
    def complete_registry(self):
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)) or not REQUIRED_RULES <= set(ids):
            raise ValueError("safety policy has duplicate or missing required rules")
        return self


class RuleResult(Contract):
    rule_id: str
    status: Literal["PASS", "BREACH", "UNKNOWN"]
    reason: str
    source: str
    limiting_value: float | None = None


class PolicyResult(Contract):
    policy_id: str
    policy_version: str
    policy_sha256: str
    overall: Literal["PASS", "BREACH", "UNKNOWN"]
    safety_gate_passed: bool
    rules: list[RuleResult]


def load_demo_policy(path: Path = POLICY_PATH) -> SafetyPolicy:
    return SafetyPolicy.model_validate_json(path.read_text())


def _combine(statuses: list[str]) -> Literal["PASS", "BREACH", "UNKNOWN"]:
    if "BREACH" in statuses:
        return "BREACH"
    if "UNKNOWN" in statuses or not statuses:
        return "UNKNOWN"
    return "PASS"


def evaluate_policy(
    policy: SafetyPolicy,
    context: ResolvedContext,
    *,
    planning_safety: dict[datetime, SafetyResult] | None = None,
) -> PolicyResult:
    """Check every applicable rule in every half-hour of the case window."""
    planning = {utc(time): result for time, result in (planning_safety or {}).items()}
    times = [utc(context.case.starts_at) + timedelta(minutes=30 * index) for index in range(48)]
    results: list[RuleResult] = []
    for rule in policy.rules:
        if "*" not in rule.applies_to and not set(rule.applies_to).intersection(context.case.scenario_ids):
            continue
        if not rule.approved:
            results.append(RuleResult(rule_id=rule.rule_id, status="UNKNOWN", reason="Rule has no approved calculation or limit", source=rule.source))
            continue
        interval_statuses: list[str] = []
        values: list[float] = []
        for time in times:
            if rule.calculation == "planning_dc":
                screen = planning.get(time)
                check = (screen.thermal if rule.rule_id == "network_loading" else screen.islanding) if screen else None
                interval_statuses.append({"PASS": "PASS", "FAIL": "BREACH", "UNKNOWN": "UNKNOWN"}[check.status] if check else "UNKNOWN")
                continue
            field = rule.required_inputs[0]
            matches = [item for item in context.values.get(field, []) if item.evidence.valid_at is not None and utc(item.evidence.valid_at) == time]
            item = matches[0] if matches else None
            if item is None or item.status != "available" or not isinstance(item.evidence.value, (int, float)) or isinstance(item.evidence.value, bool):
                interval_statuses.append("UNKNOWN")
                continue
            number = float(item.evidence.value)
            values.append(number)
            assert rule.limit is not None
            passes = number <= rule.limit if rule.calculation == "max_le" else number >= rule.limit
            interval_statuses.append("PASS" if passes else "BREACH")
        status = _combine(interval_statuses)
        results.append(RuleResult(
            rule_id=rule.rule_id, status=status,
            reason="At least one interval breaches the rule" if status == "BREACH" else "One or more intervals lack a passing check" if status == "UNKNOWN" else "All intervals passed the stated demo check",
            source=rule.source,
            limiting_value=(max(values) if rule.calculation == "max_le" else min(values)) if values else None,
        ))
    overall = _combine([item.status for item in results])
    fingerprint = hashlib.sha256(policy.model_dump_json().encode()).hexdigest()
    return PolicyResult(policy_id=policy.policy_id, policy_version=policy.version,
                        policy_sha256=fingerprint, overall=overall,
                        safety_gate_passed=overall == "PASS", rules=results)

"""Action-specific operational evidence gates for candidate interventions.

These checks sit after scenario/action resolution and alongside the physical
network screen. They do not infer authority, permissions, capability, or
timing from the action type. Missing evidence stays UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Mapping

from pydantic import Field, model_validator

from backend.app.safety import CheckResult, combine_checks

from .contracts import Contract, DecisionCase, utc


class ActionOperationalEvidence(Contract):
    named_asset_or_party: str | None = None
    authority_status: Literal["confirmed", "denied", "not_required", "unknown"] | None = None
    permission_status: Literal["confirmed", "denied", "not_required", "unknown"] | None = None
    availability_status: Literal["available", "unavailable", "unknown"] | None = None
    response_time_minutes: float | None = Field(default=None, ge=0)
    sustain_duration_minutes: float | None = Field(default=None, gt=0)
    capability_mw: float | None = Field(default=None, ge=0)
    side_effects_review_status: Literal[
        "reviewed", "blocking", "not_required", "unreviewed"
    ] | None = None
    evidence_reference: str
    available_at: datetime
    max_age_seconds: int = Field(ge=0)
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def valid_reference(self):
        if not self.evidence_reference.strip():
            raise ValueError("operational action evidence needs an evidence reference")
        if self.named_asset_or_party is not None and not self.named_asset_or_party.strip():
            raise ValueError("named asset or party must be nonempty when supplied")
        utc(self.available_at)
        if self.valid_until is not None:
            utc(self.valid_until)
            if utc(self.valid_until) < utc(self.available_at):
                raise ValueError("operational evidence validity cannot end before availability")
        return self


@dataclass(frozen=True)
class ActionOperationalResult:
    action_id: str
    asset_capability: CheckResult
    timing: CheckResult
    checks: dict[str, CheckResult]

    @property
    def overall(self) -> str:
        return combine_checks({
            "asset_capability": self.asset_capability,
            "timing": self.timing,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "overall": self.overall,
            "asset_capability": self.asset_capability.__dict__,
            "timing": self.timing.__dict__,
            "checks": {
                name: check.__dict__
                for name, check in self.checks.items()
            },
        }


@dataclass(frozen=True)
class ActionBundleOperationalResult:
    overall: str
    asset_capability: CheckResult
    timing: CheckResult
    actions: dict[str, ActionOperationalResult]

    @property
    def relief_timing_verified(self) -> bool | None:
        response_status = combine_checks({
            action_id: result.checks["response_time"]
            for action_id, result in self.actions.items()
        })
        if response_status == "PASS":
            return True
        if response_status == "FAIL":
            return False
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "asset_capability": self.asset_capability.__dict__,
            "timing": self.timing.__dict__,
            "relief_timing_verified": self.relief_timing_verified,
            "actions": {
                action_id: result.to_dict()
                for action_id, result in self.actions.items()
            },
        }


def _status_check(
    value: str | None,
    *,
    pass_values: set[str],
    fail_values: set[str],
    missing_reason: str,
    pass_reason: str,
    fail_reason: str,
    evidence: str | None,
) -> CheckResult:
    if value is None or value == "unknown" or value == "unreviewed":
        return CheckResult("UNKNOWN", missing_reason, evidence)
    if value in fail_values:
        return CheckResult("FAIL", fail_reason, evidence)
    if value in pass_values:
        return CheckResult("PASS", pass_reason, evidence)
    return CheckResult("UNKNOWN", missing_reason, evidence)


def _missing_action_result(action_id: str) -> ActionOperationalResult:
    missing = CheckResult(
        "UNKNOWN",
        "No structured operational evidence was supplied for this action instance.",
    )
    return ActionOperationalResult(
        action_id=action_id,
        asset_capability=missing,
        timing=missing,
        checks={
            "identity": missing,
            "location": missing,
            "authority": missing,
            "permission": missing,
            "availability": missing,
            "response_time": missing,
            "duration": missing,
            "capability": missing,
            "side_effects": missing,
        },
    )


def evaluate_action_operational_safety(
    candidate: Mapping[str, Any],
    case: DecisionCase,
) -> ActionOperationalResult:
    """Evaluate action-specific execution evidence without inventing missing facts."""
    action_id = str(candidate.get("action_id", "")).strip()
    if not action_id:
        raise ValueError("action candidate needs an action_id")

    payload = candidate.get("operational_evidence")
    if payload is None:
        return _missing_action_result(action_id)
    if not isinstance(payload, Mapping):
        raise ValueError("operational_evidence must be an object")
    evidence = ActionOperationalEvidence.model_validate(dict(payload))
    reference = evidence.evidence_reference
    available_at = utc(evidence.available_at)
    decision_time = utc(case.as_of)
    if available_at > decision_time:
        raise ValueError("operational action evidence was unavailable at the decision time")
    evidence_age = (decision_time - available_at).total_seconds()
    if evidence_age > evidence.max_age_seconds:
        stale = CheckResult(
            "UNKNOWN",
            "Operational action evidence exceeds its declared freshness limit.",
            reference,
        )
        return ActionOperationalResult(
            action_id=action_id,
            asset_capability=stale,
            timing=stale,
            checks={
                "identity": stale,
                "location": stale,
                "authority": stale,
                "permission": stale,
                "availability": stale,
                "response_time": stale,
                "duration": stale,
                "capability": stale,
                "side_effects": stale,
            },
        )

    candidate_identity = (
        evidence.named_asset_or_party
        or str(candidate.get("asset_id", "")).strip()
        or str(candidate.get("source_asset_id", "")).strip()
        or str(candidate.get("renewable_group_id", "")).strip()
        or str(candidate.get("interconnector_id", "")).strip()
    )
    identity = (
        CheckResult(
            "PASS",
            f"Named action asset or party: {candidate_identity}.",
            reference,
        )
        if candidate_identity
        else CheckResult(
            "UNKNOWN",
            "No named asset or responsible party was supplied.",
            reference,
        )
    )

    review_status = str(candidate.get("review_status", ""))
    if review_status in {"accepted_proxy", "accepted_verified"}:
        location = CheckResult(
            "PASS",
            (
                "Action location is accepted for the planning screen."
                if review_status == "accepted_verified"
                else "Action location is an accepted planning proxy, not a live verified location."
            ),
            str(candidate.get("evidence_reference", "")).strip() or reference,
        )
    elif review_status == "scenario_assumption":
        location = CheckResult(
            "UNKNOWN",
            "Action location is only a scenario assumption.",
            str(candidate.get("evidence_reference", "")).strip() or reference,
        )
    else:
        location = CheckResult(
            "UNKNOWN",
            "Action location review status is unavailable.",
            reference,
        )

    authority = _status_check(
        evidence.authority_status,
        pass_values={"confirmed", "not_required"},
        fail_values={"denied"},
        missing_reason="Authority to issue the action is not confirmed.",
        pass_reason="Authority to issue the action is confirmed or not required.",
        fail_reason="Authority to issue the action is denied.",
        evidence=reference,
    )
    permission = _status_check(
        evidence.permission_status,
        pass_values={"confirmed", "not_required"},
        fail_values={"denied"},
        missing_reason="Required action permission is not confirmed.",
        pass_reason="Required action permission is confirmed or not required.",
        fail_reason="Required action permission is denied.",
        evidence=reference,
    )
    availability = _status_check(
        evidence.availability_status,
        pass_values={"available"},
        fail_values={"unavailable"},
        missing_reason="Asset or party availability is not confirmed.",
        pass_reason="Asset or party availability is confirmed.",
        fail_reason="Asset or party is unavailable.",
        evidence=reference,
    )

    available_from = utc(_parse_candidate_time(candidate, "available_from"))
    available_until = utc(_parse_candidate_time(candidate, "available_until"))
    target_start = max(utc(case.starts_at), available_from)
    if available_until <= target_start:
        availability = CheckResult(
            "FAIL",
            "The proposed action window does not overlap the decision window.",
            reference,
        )
    elif evidence.valid_until is not None and utc(evidence.valid_until) < target_start:
        availability = CheckResult(
            "UNKNOWN",
            "Operational availability evidence does not remain valid through the first target interval.",
            reference,
        )

    if evidence.response_time_minutes is None:
        response_time = CheckResult(
            "UNKNOWN",
            "No response-time evidence was supplied.",
            reference,
        )
    else:
        ready_at = utc(case.as_of) + timedelta(minutes=evidence.response_time_minutes)
        response_time = CheckResult(
            "PASS" if ready_at <= target_start else "FAIL",
            (
                f"Action can respond by {ready_at.isoformat()}, before its first "
                f"target interval at {target_start.isoformat()}."
                if ready_at <= target_start
                else
                f"Action would not respond until {ready_at.isoformat()}, after its "
                f"first target interval at {target_start.isoformat()}."
            ),
            reference,
            value=float(evidence.response_time_minutes),
            unit="minutes",
        )

    requested_duration = (available_until - available_from).total_seconds() / 60.0
    if evidence.sustain_duration_minutes is None:
        duration = CheckResult(
            "UNKNOWN",
            "No sustained-duration evidence was supplied.",
            reference,
        )
    else:
        duration = CheckResult(
            "PASS" if evidence.sustain_duration_minutes + 1e-9 >= requested_duration else "FAIL",
            (
                f"Supplied sustain duration {evidence.sustain_duration_minutes:.2f} min "
                f"covers requested action window {requested_duration:.2f} min."
                if evidence.sustain_duration_minutes + 1e-9 >= requested_duration
                else
                f"Supplied sustain duration {evidence.sustain_duration_minutes:.2f} min "
                f"is shorter than requested action window {requested_duration:.2f} min."
            ),
            reference,
            value=float(evidence.sustain_duration_minutes),
            unit="minutes",
        )

    requested_mw = float(candidate.get("power_mw", 0.0))
    derived_limit = _derived_candidate_capability(candidate)
    capability_limit = (
        float(evidence.capability_mw)
        if evidence.capability_mw is not None
        else derived_limit
    )
    if capability_limit is None:
        capability = CheckResult(
            "UNKNOWN",
            "No action-specific MW capability evidence was supplied.",
            reference,
        )
    else:
        capability = CheckResult(
            "PASS" if requested_mw <= capability_limit + 1e-9 else "FAIL",
            (
                f"Requested {requested_mw:.2f} MW is within evidenced capability "
                f"{capability_limit:.2f} MW."
                if requested_mw <= capability_limit + 1e-9
                else
                f"Requested {requested_mw:.2f} MW exceeds evidenced capability "
                f"{capability_limit:.2f} MW."
            ),
            reference,
            value=capability_limit,
            unit="MW",
        )

    side_effects = _status_check(
        evidence.side_effects_review_status,
        pass_values={"reviewed", "not_required"},
        fail_values={"blocking"},
        missing_reason="Potential side effects have not been reviewed.",
        pass_reason="Potential side effects were reviewed or are not applicable.",
        fail_reason="The side-effects review found a blocking issue.",
        evidence=reference,
    )

    asset_checks = {
        "identity": identity,
        "location": location,
        "availability": availability,
        "duration": duration,
        "capability": capability,
        "side_effects": side_effects,
    }
    timing_checks = {
        "authority": authority,
        "permission": permission,
        "response_time": response_time,
    }
    asset_capability = CheckResult(
        combine_checks(asset_checks),
        "Action-specific asset capability, availability, duration, location and side-effects gate.",
        reference,
    )
    timing = CheckResult(
        combine_checks(timing_checks),
        "Action authority, permission and response-time gate.",
        reference,
    )
    return ActionOperationalResult(
        action_id=action_id,
        asset_capability=asset_capability,
        timing=timing,
        checks={**asset_checks, **timing_checks},
    )


def evaluate_action_bundle_operational_safety(
    candidates: list[Mapping[str, Any]],
    case: DecisionCase,
) -> ActionBundleOperationalResult:
    """Require every member of a bundle to pass the action-specific gates."""
    actions = {
        str(candidate["action_id"]): evaluate_action_operational_safety(candidate, case)
        for candidate in candidates
    }
    if not actions:
        unknown = CheckResult("UNKNOWN", "No action instances were supplied.")
        return ActionBundleOperationalResult(
            overall="UNKNOWN",
            asset_capability=unknown,
            timing=unknown,
            actions={},
        )

    asset_status = combine_checks({
        action_id: result.asset_capability
        for action_id, result in actions.items()
    })
    timing_status = combine_checks({
        action_id: result.timing
        for action_id, result in actions.items()
    })
    asset = CheckResult(
        asset_status,
        "Every bundled action must pass its action-specific asset gate.",
    )
    timing = CheckResult(
        timing_status,
        "Every bundled action must pass its authority, permission and timing gate.",
    )
    overall = combine_checks({
        "asset_capability": asset,
        "timing": timing,
    })
    return ActionBundleOperationalResult(
        overall=overall,
        asset_capability=asset,
        timing=timing,
        actions=actions,
    )


def _parse_candidate_time(candidate: Mapping[str, Any], field: str):
    from backend.app.network_forecast import _parse_time

    if field not in candidate:
        raise ValueError(f"action candidate missing {field}")
    return _parse_time(str(candidate[field]))


def _derived_candidate_capability(candidate: Mapping[str, Any]) -> float | None:
    family = str(candidate.get("contract_action_id") or "FLEX_LOAD")
    if family != "GENERATOR_REDISPATCH":
        return None
    fields = (
        "source_down_headroom_mw",
        "replacement_up_headroom_mw",
        "source_ramp_limit_mw",
        "replacement_ramp_limit_mw",
    )
    if any(field not in candidate for field in fields):
        return None
    return min(float(candidate[field]) for field in fields)

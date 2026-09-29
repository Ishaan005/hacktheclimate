"""Issue #61 operator workspace contract and evidence-gated assessment.

This endpoint prepares a complete screen from reviewed case inputs. It does not
promote the repository's planning screens to an operational safety approval.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import Field, model_validator

from .decision.contracts import Contract, DecisionCase, EvidenceValue, utc
from .decision.scenarios import SCENARIO_IDS, load_scenario_catalogue

router = APIRouter(prefix="/v1/workspace", tags=["operator workspace"])

FactState = Literal["current", "stale", "missing", "conflicting"]
CheckState = Literal["PASS", "FAIL", "UNKNOWN"]

FAMILY_CHECKS = {
    "transmission": ("normal_route_flow", "credible_failure_flow", "relief_before_breach", "voltage_and_system_strength"),
    "high_frequency_minimum_generation": ("frequency_and_response", "qualified_unit_minimum", "reserve_by_service", "ramp_by_deadline"),
    "snsp": ("all_island_snsp", "inertia", "rocof_and_stability", "rebound"),
}

ACTION_CHECKS = {
    "GENERATOR_REDISPATCH": ("matched_mw", "unit_range_and_ramp", "temporary_balance_and_reserve"),
    "NETWORK_SWITCHING": ("switch_sequence_clearance", "breaker_and_protection", "fault_current_and_islanding"),
    "OUTAGE_RETURN": ("work_party_release", "fitness_to_energise", "switching_permission_and_time"),
    "FLEX_LOAD": ("metered_local_relief", "load_duration", "post_trip_connection_and_rebound"),
    "STORAGE_CHARGE": ("metered_local_relief", "energy_and_duration", "service_headroom", "rebound"),
    "RENEWABLE_LIMIT": ("group_membership", "setpoint_and_incremental_mw"),
    "INTERCONNECTOR_TRANSFER": ("accepted_signed_mw", "headroom_and_ramp", "delivery_and_tso_agreement"),
    "UNIT_COMMITMENT": ("qualified_unit_count", "inertia_during_changeover", "incoming_readiness"),
    "RESERVE_RAMP_ACTION": ("service_and_direction", "response_and_sustain", "deadline_delivery"),
}

CHECK_FACTS = {
    "normal_route_flow": ("normal_flow_mw", "normal_flow_limit_mw", "MW"),
    "credible_failure_flow": ("post_failure_flow_mw", "post_failure_limit_mw", "MW"),
    "frequency_and_response": ("measured_frequency_hz", "effective_high_frequency_limit_hz", "Hz"),
    "qualified_unit_minimum": ("online_qualified_unit_count", "required_qualified_unit_count", "units"),
    "reserve_by_service": ("qualified_available_reserve_mw", "reserve_requirement_mw", "MW"),
    "ramp_by_deadline": ("qualified_available_ramp_capability_mw", "required_ramp_capability_mw", "MW"),
    "all_island_snsp": ("snsp_ratio_pct", "effective_snsp_limit_pct", "%"),
}


def _field_unit(field: str) -> str | None:
    if field.endswith("_mw"):
        return "MW"
    if field.endswith("_mwh"):
        return "MWh"
    if field.endswith("_hz"):
        return "Hz"
    if field.endswith("_pct"):
        return "%"
    if field.endswith("_count"):
        return "units"
    return None


class PlanStep(Contract):
    step_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    asset_or_party: str | None = None
    executor: str | None = None
    permission: Literal["confirmed", "pending", "denied", "unknown"] = "unknown"
    starts_at: datetime | None = None
    effect_at: datetime | None = None
    ends_at: datetime | None = None
    limiting_location_delta_mw: float | None = None
    depends_on: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_times(self):
        times = [utc(t) for t in (self.starts_at, self.effect_at, self.ends_at) if t is not None]
        if times != sorted(times):
            raise ValueError("step times must be ordered")
        if self.step_id in self.depends_on or len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError("step dependencies must be unique and cannot refer to self")
        return self


class Plan(Contract):
    steps: list[PlanStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_dependencies(self):
        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen:
                raise ValueError("step IDs must be unique")
            if not set(step.depends_on) <= seen:
                raise ValueError("dependencies must refer to earlier steps")
            seen.add(step.step_id)
        return self


class WorkspaceAssessmentRequest(Contract):
    decision_case: DecisionCase
    view: Literal["national", "site"] = "national"
    site_id: str | None = None
    evidence: list[EvidenceValue] = Field(default_factory=list)
    proposed_plan: Plan = Field(default_factory=Plan)
    operator_alternative: Plan = Field(default_factory=Plan)

    @model_validator(mode="after")
    def valid_view(self):
        if self.view == "site" and not (self.site_id or self.decision_case.location):
            raise ValueError("site view needs a site ID or case location")
        unknown = set(self.decision_case.scenario_ids) - SCENARIO_IDS
        if unknown:
            raise ValueError(f"unknown locked scenario IDs: {', '.join(sorted(unknown))}")
        return self


def _fact_rows(request: WorkspaceAssessmentRequest) -> tuple[list[dict[str, Any]], dict[str, FactState]]:
    by_field: dict[str, list[EvidenceValue]] = {}
    for item in request.evidence:
        by_field.setdefault(item.field, []).append(item)
    for instruction in request.decision_case.existing_instructions:
        by_field.setdefault("active_instructions", []).append(EvidenceValue(
            field="active_instructions", value=instruction.instruction_id, unit="instruction",
            source_type="operator", source=instruction.evidence_reference,
            source_version="case", available_at=request.decision_case.as_of,
            max_age_seconds=0,
        ))
    catalogue = load_scenario_catalogue()
    selected_definitions = [definition for definition in catalogue.definitions if definition.scenario_id in request.decision_case.scenario_ids]
    wanted = {field for definition in selected_definitions for field in definition.intake_fields}
    field_families = {field: definition.family for definition in selected_definitions for field in definition.intake_fields}
    wanted.add("active_instructions")
    rows: list[dict[str, Any]] = []
    states: dict[str, FactState] = {}
    decision_time = utc(request.decision_case.as_of)
    for field in sorted(wanted | by_field.keys()):
        values = by_field.get(field, [])
        current = [item for item in values if item.value is not None and item.available_at is not None
                   and utc(item.available_at) <= decision_time
                   and (decision_time - utc(item.available_at)).total_seconds() <= (item.max_age_seconds or 0)]
        distinct = {(json.dumps(item.value, sort_keys=True), item.unit) for item in current}
        state: FactState = ("conflicting" if len(distinct) > 1 else "current" if current else
                            "stale" if any(item.value is not None for item in values) else "missing")
        selected = current[-1] if current else values[-1] if values else None
        rows.append({"field": field, "family": field_families.get(field, "general"),
                     "value": selected.value if selected and state != "conflicting" else None,
                     "unit": selected.unit if selected else _field_unit(field),
                     "source": selected.source if selected else None,
                     "source_version": selected.source_version if selected else None,
                     "source_type": selected.source_type if selected else None,
                     "available_at": selected.available_at.isoformat() if selected and selected.available_at else None,
                     "observed_at": selected.observed_at.isoformat() if selected and selected.observed_at else None,
                     "issued_at": selected.issued_at.isoformat() if selected and selected.issued_at else None,
                     "valid_at": selected.valid_at.isoformat() if selected and selected.valid_at else None,
                     "state": state,
                     "reason": "Current sources disagree" if state == "conflicting" else
                     "Evidence is older than its freshness limit or postdates the decision" if state == "stale" else
                     "No evidence supplied" if state == "missing" else None,
                     "observations": [item.model_dump(mode="json") for item in values],
                     "operator_edit": bool(selected and selected.source_type == "operator")})
        states[field] = state
    return rows, states


def _check(check_id: str, family: str, reason: str, *, action_step_id: str | None = None,
           status: CheckState = "UNKNOWN") -> dict[str, Any]:
    return {"check_id": check_id, "family": family, "action_step_id": action_step_id,
            "status": status, "value": None, "unit": None, "effective_limit": None,
            "margin": None, "worst_time": None, "worst_failure": None,
            "source": None, "reason": reason}


def _family_check(check_id: str, family: str, facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    check = _check(check_id, family, "Validated operational assessment and effective rule are not connected")
    pair = CHECK_FACTS.get(check_id)
    if pair is None:
        return check
    value_field, limit_field, unit = pair
    value, limit = facts.get(value_field), facts.get(limit_field)
    if value and value["state"] == "current":
        check["value"] = value["value"]
        check["unit"] = unit
        check["source"] = value["source"]
        check["worst_time"] = value["valid_at"] or value["observed_at"]
    if limit and limit["state"] == "current":
        check["effective_limit"] = limit["value"]
    if (isinstance(check["value"], (int, float)) and not isinstance(check["value"], bool)
            and isinstance(check["effective_limit"], (int, float)) and not isinstance(check["effective_limit"], bool)):
        check["margin"] = (check["value"] - check["effective_limit"] if check_id in {"qualified_unit_minimum", "reserve_by_service", "ramp_by_deadline"}
                           else check["effective_limit"] - check["value"])
        check["reason"] = "Reported value and limit shown for review; approved rule and study are not connected"
    if check_id == "credible_failure_flow" and facts.get("credible_failure", {}).get("state") == "current":
        check["worst_failure"] = facts["credible_failure"]["value"]
    return check


def _benefits() -> dict[str, Any]:
    names = ("constraint_mwh", "curtailment_mwh", "avoided_dispatch_down_mwh",
             "site_risk", "system_resource_cost_eur", "gross_market_opportunity_eur",
             "net_financial_value_eur", "carbon_tco2e")
    return {name: {"value": None, "unit": "MWh" if name.endswith("mwh") else
                    "EUR" if name.endswith("eur") else "tCO2e" if name == "carbon_tco2e" else None,
                    "method": None, "uncertainty": None, "source": None,
                    "reason": "Not established by validated case-level outcome evidence"}
            for name in names}


def _plan_state(name: str, plan: Plan, family_checks: list[dict[str, Any]],
                window: dict[str, str], active_instructions: list[dict[str, Any]],
                scenario_ids: set[str]) -> dict[str, Any]:
    checks = [dict(item) for item in family_checks]
    for step in plan.steps:
        action_checks = ACTION_CHECKS.get(step.action_id)
        if action_checks is None:
            checks.append(_check("unsupported_action", "action", f"No reviewed check set for {step.action_id}", action_step_id=step.step_id))
        else:
            for check_id in action_checks:
                checks.append(_check(check_id, "action", "No validated action-specific study or approved rule is connected", action_step_id=step.step_id))
        extras: list[str] = []
        if "H1" in scenario_ids and step.action_id == "INTERCONNECTOR_TRANSFER":
            extras.append("emergency_response_direction_approval")
        if "H1" in scenario_ids and step.action_id == "STORAGE_CHARGE":
            extras.append("seconds_response_and_observed_delivery")
        if "SNSP" in scenario_ids and step.action_id in {"FLEX_LOAD", "STORAGE_CHARGE"}:
            extras.append("full_snsp_ratio_duration_and_rebound")
        if "SNSP" in scenario_ids and step.action_id == "RENEWABLE_LIMIT":
            extras.append("measured_output_snsp")
        if "H2" in scenario_ids and step.action_id in {"GENERATOR_REDISPATCH", "UNIT_COMMITMENT"}:
            extras.append("unit_count_and_inertia_through_changeover")
        for check_id in extras:
            checks.append(_check(check_id, "action", "Scenario-specific validated evidence is not connected", action_step_id=step.step_id))
        checks.append(_check("permission", "action",
                             "Permission denied" if step.permission == "denied" else
                             "Permission awaits acceptance" if step.permission == "pending" else
                             "Permission evidence is not connected to an approved authority source",
                             action_step_id=step.step_id,
                             status="FAIL" if step.permission == "denied" else "UNKNOWN"))
    if plan.steps:
        checks.append(_check("other_affected_limits", "cross_family",
                             "The full action combination has not been studied for other affected limits"))
    safety: CheckState = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "UNKNOWN"
    label = "Unsafe" if safety == "FAIL" else "Insufficient evidence"
    permission_state = ("denied" if any(step.permission == "denied" for step in plan.steps) else
                        "pending" if any(step.permission == "pending" for step in plan.steps) else
                        "unknown" if any(step.permission == "unknown" for step in plan.steps) else "confirmed")
    return {"state": name, "window": window, "plan": plan.model_dump(mode="json"),
            "active_instructions": active_instructions, "permission_state": permission_state,
            "safety": {"status": safety, "reason": "Required validated safety checks are unavailable" if safety == "UNKNOWN" else "A required check failed",
                       "missing_checks": [c["check_id"] for c in checks if c["status"] == "UNKNOWN"]},
            "plan_label": label, "checks": checks,
            "delivered_relief_mw": None, "response_time_seconds": None,
            "time_to_breach_seconds": None, "worst_limit_margin": None,
            "benefits": _benefits()}


@router.get("/brief")
def workspace_brief() -> dict[str, Any]:
    catalogue = load_scenario_catalogue()
    return {"schema_version": 1, "scenario_catalogue": catalogue.model_dump(mode="json"),
            "views": ["national", "site"], "action_check_ids": ACTION_CHECKS,
            "source_statuses": ["live", "historical_demonstration", "planning_case", "no_live_connection"]}


@router.post("/assess")
def assess_workspace(request: WorkspaceAssessmentRequest) -> dict[str, Any]:
    case = request.decision_case
    if utc(case.as_of) > datetime.now(timezone.utc) + timedelta(minutes=1):
        raise HTTPException(422, "case decision time cannot be in the future")
    facts, states = _fact_rows(request)
    catalogue = load_scenario_catalogue()
    selected = [definition for definition in catalogue.definitions if definition.scenario_id in case.scenario_ids]
    bindings = [{"scenario_id": definition.scenario_id, "name": definition.name,
                 "family": definition.family, "classification_verified": False,
                 "missing_fields": [field for field in definition.intake_fields if states.get(field) != "current"]}
                for definition in selected]
    families = {definition.family for definition in selected}
    # The site view keeps every selected all-island family check.
    fact_by_field = {row["field"]: row for row in facts}
    checks = [_family_check(check_id, family, fact_by_field)
              for family in sorted(families) for check_id in FAMILY_CHECKS[family]]
    if not checks:
        checks = [_check("limiting_cause", "intake", "Cause unknown; select a locked scenario after reviewing facts")]
    window = {"starts_at": case.starts_at.isoformat(), "ends_at": case.ends_at.isoformat()}
    active_instructions = [item.model_dump(mode="json") for item in case.existing_instructions]
    empty = Plan()
    states_out = {
        "current_plan": _plan_state("current_plan", empty, checks, window, active_instructions, set(case.scenario_ids)),
        "no_new_instruction": _plan_state("no_new_instruction", empty, checks, window, active_instructions, set(case.scenario_ids)),
        "proposed_plan": _plan_state("proposed_plan", request.proposed_plan, checks, window, active_instructions, set(case.scenario_ids)),
        "operator_alternative": _plan_state("operator_alternative", request.operator_alternative, checks, window, active_instructions, set(case.scenario_ids)),
    }
    fingerprint = sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    return {"schema_version": 1, "case_id": case.case_id, "revision": fingerprint,
            "assessment_id": f"workspace-{fingerprint[:16]}", "assessed_at": now,
            "view": request.view, "location": request.site_id or case.location,
            "decision_time": case.as_of.isoformat(), "window": window,
            "source_status": "no_live_connection", "data_status": "incomplete",
            "bindings": bindings, "facts": facts,
            "active_instructions": active_instructions,
            "comparisons": states_out,
            "evidence": {"scenario_catalogue_source": catalogue.source,
                         "scenario_catalogue_version": catalogue.schema_version,
                         "safety_policy_version": None, "model_version": None,
                         "assumptions": [],
                         "missing_checks": sorted({c["check_id"] for state in states_out.values() for c in state["checks"] if c["status"] == "UNKNOWN"}),
                         "audit_id": f"workspace-{fingerprint[:16]}",
                         "audit_persisted": False,
                         "reason": "No live operational feed or approved safety study is connected to this endpoint"}}

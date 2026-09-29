"""Issue #61 operator workspace contract and evidence-gated assessment.

This endpoint prepares a complete screen from reviewed case inputs. It does not
promote the repository's planning screens to an operational safety approval.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import Any, Literal, Mapping

from fastapi import APIRouter, HTTPException
from pydantic import Field, model_validator

from .decision.contracts import Contract, DecisionCase, EvidenceValue, utc
from .decision.scenarios import SCENARIO_IDS, load_scenario_catalogue
from .decision.sources import load_checked_constraint
from .workspace import _evaluate_live_case

router = APIRouter(prefix="/v1/workspace", tags=["operator workspace"])

FactState = Literal["current", "stale", "missing", "conflicting", "modeled"]
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


def _missing_reason(field: str) -> str:
    specific = {
        "active_instructions": "No connected instruction log; an empty request does not confirm that none are active",
        "limiting_equipment": "No named limiting equipment or reviewed asset mapping supplied",
        "outage_equipment": "No confirmed out-of-service equipment supplied",
        "expected_return_time": "No current outage schedule or confirmed return time supplied",
        "affected_renewable_units_or_groups": "No reviewed affected-unit or generator crosswalk supplied",
        "reach": "No reviewed network reach or affected-area mapping supplied",
        "what_changed": "No dated event or change record supplied",
    }
    if field in specific:
        return specific[field]
    if field in {"normal_flow_mw", "post_failure_flow_mw", "measured_frequency_hz", "snsp_ratio_pct"}:
        return "No decision-time operational measurement or reviewed forecast supplied"
    if field.endswith("_limit_mw") or field.endswith("_limit_hz") or field.endswith("_limit_pct") or field in {"effective_policy", "required_qualified_unit_count", "reserve_requirement_mw"}:
        return "No effective, reviewed limit or policy supplied"
    return "No source supplied for this case"


class ConditionContext(Contract):
    scenario_id: str = Field(min_length=1)
    situation_key: str | None = None
    reach: Literal["local_area", "shared_route", "wide_group"] | None = None
    limiting_asset: str | None = None
    outage_type: Literal["planned", "forced"] | None = None
    time_setting: Literal["now", "forecast"] | None = None
    snsp_drivers: list[str] = Field(default_factory=list)
    jurisdiction: Literal["ireland", "northern_ireland", "both"] | None = None


class PlanStep(Contract):
    step_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    role: Literal["main", "supporting", "parallel"] = "main"
    instruction: str | None = None
    asset_or_party: str | None = None
    executor: str | None = None
    permission_route: Literal["direct", "needs_clearance", "needs_acceptance"] = "direct"
    permission: Literal["confirmed", "pending", "denied", "unknown"] = "unknown"
    permission_party: str | None = None
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
    description: str = ""
    conditions: list[ConditionContext] = Field(default_factory=list)
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
        condition_ids = {item.scenario_id for item in self.conditions}
        if condition_ids - SCENARIO_IDS:
            raise ValueError("condition context contains an unknown locked scenario ID")
        if condition_ids and condition_ids != set(self.decision_case.scenario_ids):
            raise ValueError("condition context must match decision-case scenario IDs")
        return self


def _fact_rows(request: WorkspaceAssessmentRequest, planning_scenario: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, FactState]]:
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
    field_families["planning_rate_a_mva"] = "transmission"
    wanted.add("active_instructions")
    decision_time = utc(request.decision_case.as_of)

    def add_case_fact(field: str, value: str | None, source: str) -> None:
        if value and field in wanted and field not in by_field:
            by_field[field] = [EvidenceValue(
                field=field, value=value, unit="", source_type="operator",
                source=source, source_version="workspace-case-v1",
                available_at=decision_time, max_age_seconds=24 * 3600,
                limitation="Case context only; not independently verified against an operational feed",
            )]

    for condition in request.conditions:
        add_case_fact("limiting_equipment", condition.limiting_asset, "Case condition context")
        add_case_fact("reach", condition.reach, "Case condition context")
        add_case_fact("outage_type", condition.outage_type, "Case condition context")
        add_case_fact("now_or_forecast", condition.time_setting, "Case condition context")
        add_case_fact("jurisdiction", condition.jurisdiction, "Case condition context")
    description = request.description.lower()
    if re.search(r"\bplanned\s+outage\b", description):
        add_case_fact("outage_type", "planned", "Operator description")
    elif re.search(r"\bforced\s+outage\b", description):
        add_case_fact("outage_type", "forced", "Operator description")
    duration = re.search(r"\bnext\s+(\d{1,2})\s+hours?\b", description)
    if duration and 0 < int(duration.group(1)) <= 24:
        add_case_fact("relevant_time_window", f"Next {int(duration.group(1))} hours from decision time", "Operator description")
    add_case_fact("now_or_forecast", "forecast", "Future assessment window")
    if planning_scenario and planning_scenario.get("source") == "demo":
        planning_facts = planning_scenario.get("planningFacts")
        if isinstance(planning_facts, Mapping):
            available = datetime.fromisoformat(str(planning_scenario["modelRunAt"]).replace("Z", "+00:00"))
            valid = datetime.fromisoformat(str(planning_scenario["intervalStart"]).replace("Z", "+00:00"))
            for field, value in planning_facts.items():
                if (value is None or field in by_field or utc(available) > decision_time
                        or utc(valid) != utc(request.decision_case.starts_at)):
                    continue
                by_field[field] = [EvidenceValue(
                    field=field, value=value,
                    unit="MVA" if field == "planning_rate_a_mva" else "MW" if field == "normal_flow_mw" else "",
                    source_type="planning_model", source="Synthetic West outage planning case (not live)",
                    source_version="synthetic-golden-path-v1", available_at=available,
                    valid_at=valid, max_age_seconds=24 * 3600,
                    limitation="Synthetic four-bus DC planning case; not a measured flow, operating limit, or safety verdict",
                )]
    rows: list[dict[str, Any]] = []
    states: dict[str, FactState] = {}
    for field in sorted(wanted | by_field.keys()):
        values = by_field.get(field, [])
        current = [item for item in values if item.source_type != "planning_model" and item.value is not None and item.available_at is not None
                   and utc(item.available_at) <= decision_time
                   and (decision_time - utc(item.available_at)).total_seconds() <= (item.max_age_seconds or 0)]
        distinct = {(json.dumps(item.value, sort_keys=True), item.unit) for item in current}
        modeled = [item for item in values if item.source_type == "planning_model" and item.value is not None
                   and item.available_at is not None and utc(item.available_at) <= decision_time
                   and (decision_time - utc(item.available_at)).total_seconds() <= (item.max_age_seconds or 0)]
        state: FactState = ("conflicting" if len(distinct) > 1 else "current" if current else
                            "modeled" if modeled else
                            "stale" if any(item.value is not None for item in values) else "missing")
        selected = current[-1] if current else modeled[-1] if modeled else values[-1] if values else None
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
                     _missing_reason(field) if state == "missing" else
                     "Synthetic planning value; not operational evidence" if state == "modeled" else None,
                     "observations": [item.model_dump(mode="json") for item in values],
                     "operator_edit": bool(selected and selected.source_type == "operator")})
        states[field] = state
    return rows, states


def _national_context(case: DecisionCase) -> str | None:
    """Give the checked national forecast as context, never as a site outcome."""
    source = load_checked_constraint(case.as_of)
    if source.status != "available":
        return None
    target = utc(case.starts_at)
    row = next((item for item in source.values if item.valid_at and utc(item.valid_at) == target), None)
    if row is None or not isinstance(row.value, (int, float)):
        return None
    bounds = (
        f" (90% model interval {row.lower_bound:.1f}–{row.upper_bound:.1f})"
        if row.lower_bound is not None and row.upper_bound is not None else ""
    )
    return (
        f"Experimental national constraint forecast for {target.isoformat()}: "
        f"{row.value:.1f} MWh per half-hour{bounds}. "
        f"Issued {utc(row.issued_at).isoformat()}; source: {row.source}. "
        "National context only; no site, safety, curtailment or action effect is established."
    )


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


def _legacy_case(request: WorkspaceAssessmentRequest) -> dict[str, Any]:
    scenario_ids = set(request.decision_case.scenario_ids)
    coarse: list[str] = []
    if any(item.startswith("T") for item in scenario_ids):
        coarse.append("local_network_constraint")
    if scenario_ids & {"T3", "T4"}:
        coarse.append("planned_outage_exposure")
    if any(item.startswith("H") for item in scenario_ids) or "SNSP" in scenario_ids:
        coarse.append("system_wide_curtailment")

    facts: dict[str, dict[str, Any]] = {}
    for item in request.evidence:
        if item.value is not None:
            facts[item.field] = {"value": item.value}
    if request.decision_case.location and "affected_area" not in facts:
        facts["affected_area"] = {"value": request.decision_case.location}
    return {
        "id": request.decision_case.case_id,
        "originalText": request.description,
        "scenarios": coarse,
        "facts": facts,
    }


def _planning_plan(scenario: Mapping[str, Any]) -> Plan:
    action = scenario.get("action")
    if not isinstance(action, Mapping):
        return Plan()
    family = str(action.get("family") or "")
    action_id = {
        "flexible_demand": "FLEX_LOAD",
        "battery_storage": "STORAGE_CHARGE",
        "generator_redispatch": "GENERATOR_REDISPATCH",
        "outage_review": "OUTAGE_RETURN",
        "interconnector_transfer": "INTERCONNECTOR_TRANSFER",
    }.get(family)
    if action_id is None:
        return Plan()

    executability = str(action.get("executability") or "conditional")
    permission = "confirmed" if executability == "executable" else "pending"
    permission_route = "direct" if permission == "confirmed" else "needs_acceptance"
    details = action.get("details") if isinstance(action.get("details"), Mapping) else {}
    change_mw = details.get("changeMw")
    delta = None
    if isinstance(change_mw, (int, float)) and not isinstance(change_mw, bool):
        delta = -abs(float(change_mw)) if action_id in {"FLEX_LOAD", "STORAGE_CHARGE"} else float(change_mw)
    return Plan(steps=[PlanStep(
        step_id="planner-main",
        action_id=action_id,
        role="main",
        instruction=str(action.get("targetState") or action.get("assetName") or "Backend modeled candidate"),
        asset_or_party=str(action.get("assetName")) if action.get("assetName") else None,
        executor=str(action.get("assetName")) if action.get("assetName") else None,
        permission_route=permission_route,
        permission=permission,
        permission_party="External asset owner" if permission == "pending" else None,
        starts_at=action.get("startTime"),
        effect_at=action.get("targetTime"),
        ends_at=action.get("effectiveUntil"),
        limiting_location_delta_mw=delta,
    )])


def _planner_check(item: Mapping[str, Any], phase: str) -> dict[str, Any]:
    raw = str(item.get(phase) or "unknown")
    status: CheckState = "PASS" if raw == "within_modelled_limit" else "FAIL" if raw == "breach" else "UNKNOWN"
    name = str(item.get("name") or "planning_check")
    family = (
        "snsp" if name == "snsp" else
        "high_frequency_minimum_generation" if name == "min_generation" else
        "cross_family" if name == "scope" else
        "transmission"
    )
    return {
        "check_id": f"planning_{name}",
        "family": family,
        "action_step_id": None,
        "status": status,
        "value": item.get("baseline_value" if phase == "baseline" else "post_action_value"),
        "unit": None,
        "effective_limit": item.get("effective_limit"),
        "margin": item.get("baseline_margin" if phase == "baseline" else "post_action_margin", item.get("margin")),
        "worst_time": item.get("timestamp"),
        "worst_failure": None,
        "source": "synthetic DC planning case" if item.get("baseline_value") is not None else "existing planning evaluator",
        "reason": str(item.get("baseline_note") if phase == "baseline" and item.get("baseline_note") else item.get("note") or "Planning evaluator result"),
    }


def _refresh_state_safety(state: dict[str, Any]) -> None:
    checks = state["checks"]
    if any(item["status"] == "FAIL" for item in checks):
        status: CheckState = "FAIL"
        reason = "A required or modeled check failed"
        label = "Unsafe"
    elif checks and all(item["status"] == "PASS" for item in checks):
        status = "PASS"
        reason = "All connected checks passed"
        label = "Actionable" if state["permission_state"] == "confirmed" else "Conditional"
    else:
        status = "UNKNOWN"
        reason = "Required validated safety checks are unavailable"
        label = "Insufficient evidence"
    state["safety"] = {
        "status": status,
        "reason": reason,
        "missing_checks": [item["check_id"] for item in checks if item["status"] == "UNKNOWN"],
    }
    state["plan_label"] = label


def _apply_planning_preview(states_out: dict[str, dict[str, Any]], scenario: Mapping[str, Any]) -> None:
    guardrails = scenario.get("guardrails")
    if isinstance(guardrails, list):
        for key in ("current_plan", "no_new_instruction"):
            states_out[key]["checks"].extend(
                _planner_check(item, "baseline") for item in guardrails if isinstance(item, Mapping)
            )
            _refresh_state_safety(states_out[key])
        states_out["proposed_plan"]["checks"].extend(
            _planner_check(item, "postAction") for item in guardrails if isinstance(item, Mapping)
        )
        _refresh_state_safety(states_out["proposed_plan"])

    # The generic evaluator's dispatchDownWasteMwh combines causes; it cannot
    # be placed in the constraint row. Only the packaged demo explicitly
    # defines its scenario energy as constraint dispatch-down.
    if scenario.get("source") != "demo":
        return
    baseline = scenario.get("baseline") if isinstance(scenario.get("baseline"), Mapping) else {}
    post = scenario.get("postAction") if isinstance(scenario.get("postAction"), Mapping) else {}
    for key, source_value in (("current_plan", baseline), ("no_new_instruction", baseline), ("proposed_plan", post)):
        curtailment = source_value.get("curtailmentMwh")
        if isinstance(curtailment, (int, float)) and not isinstance(curtailment, bool):
            states_out[key]["benefits"]["curtailment_mwh"] = {
                "value": float(curtailment), "unit": "MWh",
                "method": "Synthetic demo scenario assumption; no action-level curtailment model",
                "uncertainty": None, "source": "demo_forecast_rows", "reason": None,
            }
    baseline_mwh = baseline.get("dispatchDownWasteMwh")
    post_mwh = post.get("dispatchDownWasteMwh")
    if isinstance(baseline_mwh, (int, float)) and not isinstance(baseline_mwh, bool):
        for key in ("current_plan", "no_new_instruction"):
            states_out[key]["benefits"]["constraint_mwh"] = {
                "value": float(baseline_mwh), "unit": "MWh",
                "method": "Existing backend planning/demo scenario",
                "uncertainty": None, "source": "workspace/evaluate",
                "reason": None,
            }
    if isinstance(post_mwh, (int, float)) and not isinstance(post_mwh, bool):
        states_out["proposed_plan"]["benefits"]["constraint_mwh"] = {
            "value": float(post_mwh), "unit": "MWh",
            "method": "Existing backend planning/demo scenario",
            "uncertainty": None, "source": "workspace/evaluate",
            "reason": None,
        }
    if (
        isinstance(baseline_mwh, (int, float)) and not isinstance(baseline_mwh, bool)
        and isinstance(post_mwh, (int, float)) and not isinstance(post_mwh, bool)
    ):
        states_out["proposed_plan"]["benefits"]["avoided_dispatch_down_mwh"] = {
            "value": float(baseline_mwh) - float(post_mwh), "unit": "MWh",
            "method": "No-new-instruction minus modeled candidate in the existing backend scenario",
            "uncertainty": None, "source": "workspace/evaluate",
            "reason": None,
        }


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
    planning_scenario = _evaluate_live_case(_legacy_case(request)) if request.description.strip() else None
    facts, states = _fact_rows(request, planning_scenario)
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
    proposed_plan = request.proposed_plan
    if planning_scenario and not proposed_plan.steps:
        proposed_plan = _planning_plan(planning_scenario)

    empty = Plan()
    states_out = {
        "current_plan": _plan_state("current_plan", empty, checks, window, active_instructions, set(case.scenario_ids)),
        "no_new_instruction": _plan_state("no_new_instruction", empty, checks, window, active_instructions, set(case.scenario_ids)),
        "proposed_plan": _plan_state("proposed_plan", proposed_plan, checks, window, active_instructions, set(case.scenario_ids)),
        "operator_alternative": _plan_state("operator_alternative", request.operator_alternative, checks, window, active_instructions, set(case.scenario_ids)),
    }
    if planning_scenario:
        _apply_planning_preview(states_out, planning_scenario)
    fingerprint = sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    return {"schema_version": 1, "case_id": case.case_id, "revision": fingerprint,
            "assessment_id": f"workspace-{fingerprint[:16]}", "assessed_at": now,
            "view": request.view, "location": request.site_id or case.location,
            "decision_time": case.as_of.isoformat(), "window": window,
            "source_status": (
                "planning_case" if planning_scenario and planning_scenario.get("source") in {"demo", "planning_case"}
                else "live" if planning_scenario and planning_scenario.get("source") == "live"
                else "no_live_connection"
            ), "data_status": "incomplete",
            "bindings": bindings, "facts": facts,
            "national_constraint_context": _national_context(case),
            "active_instructions": active_instructions,
            "comparisons": states_out,
            "evidence": {"scenario_catalogue_source": catalogue.source,
                         "scenario_catalogue_version": catalogue.schema_version,
                         "safety_policy_version": None, "model_version": None,
                         "assumptions": (
                             [str(planning_scenario.get("summary"))] if planning_scenario and planning_scenario.get("summary") else []
                         ),
                         "missing_checks": sorted({c["check_id"] for state in states_out.values() for c in state["checks"] if c["status"] == "UNKNOWN"}),
                         "audit_id": f"workspace-{fingerprint[:16]}",
                         "audit_persisted": False,
                         "reason": (
                             str(planning_scenario.get("noActionReason"))
                             if planning_scenario and planning_scenario.get("noActionReason")
                             else "No live operational feed or approved safety study is connected to this endpoint"
                         )}}

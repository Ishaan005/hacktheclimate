"""Screen a small, reviewed flexible-demand action set on future grid states."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from backend.app.network import NetworkCase, solve_dc_case
from backend.app.network_forecast import (
    DEFAULT_PLANNED_OUTAGE, _network_features, _parse_time,
    allocate_regional_generation, future_injection_adapter,
    normalized_load_shares, reviewed_generation_groups, validate_forecast_rows,
)
from backend.app.network_scenarios import Asset
from backend.app.safety import (\n    CheckResult, combine_checks, evaluate_safety, evaluate_transmission_family,\n)

MAX_CANDIDATES = 3


def load_action_candidates(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict) or not isinstance(payload.get("actions"), list):
        raise ValueError("action catalog must contain an actions list")
    return payload["actions"]


def _candidate_fields(candidate: Mapping[str, Any]) -> None:
    required = {
        "action_id", "load_bus_id", "renewable_bus_id", "allocation_region",
        "generation_type", "power_mw", "available_from", "available_until",
        "review_status", "evidence_reference",
    }
    if required - set(candidate):
        raise ValueError(f"action candidate missing fields: {sorted(required - set(candidate))}")
    if not str(candidate["action_id"]).strip() or not str(candidate["evidence_reference"]).strip():
        raise ValueError("action ID and evidence reference are required")
    if candidate["review_status"] not in {"accepted_proxy", "accepted_verified", "scenario_assumption"}:
        raise ValueError("action location needs a recognized review status")
    if candidate["generation_type"] not in {"wind", "solar"}:
        raise ValueError("action renewable generation_type must be wind or solar")
    power = float(candidate["power_mw"])
    if not math.isfinite(power) or power <= 0:
        raise ValueError("action power_mw must be positive and finite")
    start = _parse_time(str(candidate["available_from"]))
    end = _parse_time(str(candidate["available_until"]))
    if start >= end:
        raise ValueError("action availability window must have positive duration")


def _recoverable_mw(row: Mapping[str, Any], region: str, kind: str) -> float:
    by_region = row.get("recoverable_renewable_mw", {})
    if not isinstance(by_region, Mapping):
        raise ValueError("recoverable_renewable_mw must be an object")
    by_kind = by_region.get(region, {})
    if not isinstance(by_kind, Mapping):
        raise ValueError("recoverable renewable region must be an object")
    value = float(by_kind.get(kind, 0.0))
    if not math.isfinite(value) or value < 0:
        raise ValueError("recoverable renewable MW must be nonnegative and finite")
    return value


def rank_pass_actions(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order only fully passing candidates by the labeled capture upper bound."""
    return sorted(
        (row for row in evaluations if row["safety_overall"] == "PASS"),
        key=lambda row: (-row["modeled_capture_upper_bound_mwh"], row["action_id"]),
    )


def _flow_changes(base: Mapping[str, Any], changed: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the largest signed DC flow changes, including their rating proxies."""
    if base.get("status") != "ok" or changed.get("status") != "ok":
        return {"changed_asset_count": None, "max_abs_flow_change_mw": None, "top_changes": []}
    before = {(flow["asset_type"], flow["asset_id"]): flow for flow in base["flows"]}
    deltas = []
    for flow in changed["flows"]:
        key = (flow["asset_type"], flow["asset_id"])
        earlier = before.get(key)
        if earlier is None:
            continue
        delta = float(flow["flow_mw"]) - float(earlier["flow_mw"])
        if abs(delta) <= 1e-6:
            continue
        deltas.append({
            "asset_type": key[0], "asset_id": key[1],
            "base_flow_mw": float(earlier["flow_mw"]),
            "with_action_flow_mw": float(flow["flow_mw"]),
            "delta_flow_mw": delta,
            "base_loading_proxy_pct": earlier.get("loading_pct"),
            "with_action_loading_proxy_pct": flow.get("loading_pct"),
        })
    deltas.sort(key=lambda item: (-abs(item["delta_flow_mw"]), item["asset_type"], item["asset_id"]))
    return {
        "changed_asset_count": len(deltas),
        "max_abs_flow_change_mw": abs(deltas[0]["delta_flow_mw"]) if deltas else 0.0,
        "top_changes": deltas[:10],
    }


def screen_actions(
    case: NetworkCase,
    forecast_rows: list[dict[str, Any]],
    reviewed_crosswalk: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    planned_outage: Asset = DEFAULT_PLANNED_OUTAGE,
    selected_contingency: Asset | None = None,
) -> dict[str, Any]:
    """Re-solve paired renewable and flexible-load injections per active interval.

    A positive candidate MW adds the same MW at one reviewed renewable bus and
    withdraws it at one reviewed flexible-load bus. The supplied recoverable
    renewable MW is required; the national expected constraint MWh only caps a
    theoretical capture bound, not a measured or predicted local saving.
    """
    validate_forecast_rows(forecast_rows)
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError(f"at most {MAX_CANDIDATES} controlled actions are supported")
    if any(not isinstance(candidate, Mapping) for candidate in candidates):
        raise ValueError("every action candidate must be an object")
    for candidate in candidates:
        _candidate_fields(candidate)
    ids = [str(candidate["action_id"]) for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("action IDs must be unique")

    active_buses = {int(bus["bus_id"]) for bus in case.buses if bus["in_service"]}
    outage_assets = (
        case.branches if planned_outage.asset_type == "branch"
        else case.transformers if planned_outage.asset_type == "transformer"
        else None
    )
    outage_id_field = "asset_id" if planned_outage.asset_type == "branch" else "transformer_id"
    if outage_assets is None or not any(
        item[outage_id_field] == planned_outage.asset_id and item["in_service"]
        for item in outage_assets
    ):
        raise ValueError("planned outage must identify an in-service case asset")
    disabled = (
        {"disabled_branches": [planned_outage.asset_id]}
        if planned_outage.asset_type == "branch"
        else {"disabled_transformers": [planned_outage.asset_id]}
    )
    n1_disabled = dict(disabled)
    if selected_contingency is not None:
        if selected_contingency == planned_outage:
            raise ValueError("selected contingency must differ from the planned outage")
        if selected_contingency.asset_type == "branch":
            n1_disabled["disabled_branches"] = [
                *n1_disabled.get("disabled_branches", []), selected_contingency.asset_id,
            ]
        elif selected_contingency.asset_type == "transformer":
            n1_disabled["disabled_transformers"] = [
                *n1_disabled.get("disabled_transformers", []), selected_contingency.asset_id,
            ]
        else:
            raise ValueError("selected contingency asset type is unsupported")
    shares = normalized_load_shares(case)
    groups, mapping_confidence = reviewed_generation_groups(case, reviewed_crosswalk)
    evaluations = []
    for candidate in candidates:
        load_bus = int(candidate["load_bus_id"])
        renewable_bus = int(candidate["renewable_bus_id"])
        if load_bus not in active_buses or renewable_bus not in active_buses or load_bus == renewable_bus:
            raise ValueError("action buses must be distinct active buses")
        region = str(candidate["allocation_region"]).strip()
        kind = str(candidate["generation_type"])
        sites = groups.get((region, kind), [])
        bus_mec = sum(site["mec_mw"] for site in sites if site["bus_id"] == renewable_bus)
        if bus_mec <= 0:
            raise ValueError("action renewable bus lacks a reviewed region/technology match")
        start = _parse_time(str(candidate["available_from"]))
        end = _parse_time(str(candidate["available_until"]))
        power = float(candidate["power_mw"])
        intervals = []
        for row in forecast_rows:
            valid = _parse_time(str(row["valid_time"]))
            if not start <= valid < end:
                continue
            recoverable = _recoverable_mw(row, region, kind)
            injections, dc_overrides, _ = future_injection_adapter(
                case, row, load_shares=shares, generation_groups=groups,
            )
            base_renewable, _ = allocate_regional_generation(
                row.get("regional_generation_mw", {}), groups,
            )
            bus_headroom = max(0.0, bus_mec - base_renewable.get(renewable_bus, 0.0))
            cap_from_national_mwh = float(row["expected_constraint_mwh"]) / 0.5
            applied = min(power, recoverable, bus_headroom, cap_from_national_mwh)
            if applied <= 1e-8:
                intervals.append({
                    "valid_time": row["valid_time"], "applied_mw": 0.0,
                    "modeled_capture_upper_bound_mwh": 0.0,
                    "safety": None, "reason": "No explicitly recoverable renewable MW or forecast constraint MWh is available.",
                })
                continue
            changed = dict(injections)
            changed[renewable_bus] += applied
            changed[load_bus] -= applied
            base_solve = solve_dc_case(
                case, injection_overrides_mw=injections,
                dc_transfer_overrides_mw=dc_overrides, **disabled,
            )
            solve = solve_dc_case(
                case, injection_overrides_mw=changed,
                dc_transfer_overrides_mw=dc_overrides, **disabled,
            )
            n1_base = n1_action = None
            if selected_contingency is not None:
                n1_base = solve_dc_case(
                    case, injection_overrides_mw=injections,
                    dc_transfer_overrides_mw=dc_overrides, **n1_disabled,
                )
                n1_action = solve_dc_case(
                    case, injection_overrides_mw=changed,
                    dc_transfer_overrides_mw=dc_overrides, **n1_disabled,
                )
            # SNSP changes when renewable production and demand change. The
            # current national forecast supplies no validated action formula.
            planned_safety = evaluate_safety(solve).to_dict()
            n1_safety = evaluate_safety(n1_action).to_dict() if n1_action is not None else None
            transmission_family = evaluate_transmission_family(
                base_solve,
                solve,
                base_contingency_solve=n1_base,
                action_contingency_solve=n1_action,
            ).to_dict()
            overall = combine_checks({
                "planned_outage": CheckResult(planned_safety["overall"], "scenario result"),
                "transmission_family": CheckResult(
                    transmission_family["overall"], "family-level transmission result"
                ),
                **({"selected_n_minus_one": CheckResult(n1_safety["overall"], "scenario result")}
                   if n1_safety is not None else {}),
                **({"action_location": CheckResult("UNKNOWN", "Action location is a scenario assumption")}
                   if candidate["review_status"] == "scenario_assumption" else {}),
            })
            intervals.append({
                "valid_time": row["valid_time"], "applied_mw": applied,
                "modeled_capture_upper_bound_mwh": applied * 0.5,
                "safety": {
                    "overall": overall,
                    "planned_outage": planned_safety,
                    "selected_n_minus_one": n1_safety,
                    "families": {"transmission": transmission_family},
                },
                "network_effect": {
                    "planned_outage": {
                        "asset_id": planned_outage.asset_id,
                        "base": _network_features(base_solve),
                        "with_action": _network_features(solve),
                        "flow_changes": _flow_changes(base_solve, solve),
                    },
                    "selected_n_minus_one": (
                        {"asset_id": selected_contingency.asset_id,
                         "base": _network_features(n1_base),
                         "with_action": _network_features(n1_action),
                         "flow_changes": _flow_changes(n1_base, n1_action)}
                        if n1_base is not None and n1_action is not None else None
                    ),
                },
            })
        checked = [item for item in intervals if item["safety"] is not None]
        if checked:
            overall = combine_checks({
                str(index): CheckResult(item["safety"]["overall"], "interval result")
                for index, item in enumerate(checked)
            })
        else:
            overall = "UNKNOWN"
        evaluations.append({
            "action_id": str(candidate["action_id"]),
            "load_bus_id": load_bus,
            "renewable_bus_id": renewable_bus,
            "power_mw": power,
            "availability": {"from": candidate["available_from"], "until": candidate["available_until"]},
            "location_review_status": candidate["review_status"],
            "location_evidence_reference": candidate["evidence_reference"],
            "renewable_mapping_confidence": mapping_confidence,
            "safety_overall": overall,
            "modeled_capture_upper_bound_mwh": sum(
                item["modeled_capture_upper_bound_mwh"] for item in intervals
            ),
            "expected_avoided_constraint_mwh": None,
            "intervals": intervals,
        })
    ranked = rank_pass_actions(evaluations)
    return {
        "evaluated": evaluations,
        "ranked_screening_pass_actions": [item["action_id"] for item in ranked],
        "recommendation": None,
        "recommendation_reason": (
            "No fully PASS action with a validated locational avoided-constraint estimate is available."
        ),
    }


def _candidate_family(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("contract_action_id") or "FLEX_LOAD")


def _positive_finite(candidate: Mapping[str, Any], field: str) -> float:
    value = float(candidate[field])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be positive and finite")
    return value


def _bundle_candidate_fields(candidate: Mapping[str, Any]) -> None:
    common = {
        "action_id", "power_mw", "available_from", "available_until",
        "review_status", "evidence_reference",
    }
    family = _candidate_family(candidate)
    if family == "FLEX_LOAD":
        required = common | {
            "load_bus_id", "renewable_bus_id", "allocation_region", "generation_type",
        }
    elif family == "GENERATOR_REDISPATCH":
        required = common | {
            "source_asset_id", "replacement_asset_id",
            "source_bus_id", "replacement_bus_id",
            "source_down_headroom_mw", "replacement_up_headroom_mw",
            "source_ramp_limit_mw", "replacement_ramp_limit_mw",
        }
    else:
        raise ValueError(f"planning bundle executor does not support {family}")
    if required - set(candidate):
        raise ValueError(
            f"{family} action candidate missing fields: {sorted(required - set(candidate))}"
        )
    if not str(candidate["action_id"]).strip() or not str(candidate["evidence_reference"]).strip():
        raise ValueError("action ID and evidence reference are required")
    if candidate["review_status"] not in {"accepted_proxy", "accepted_verified", "scenario_assumption"}:
        raise ValueError("action location needs a recognized review status")
    _positive_finite(candidate, "power_mw")
    start = _parse_time(str(candidate["available_from"]))
    end = _parse_time(str(candidate["available_until"]))
    if start >= end:
        raise ValueError("action availability window must have positive duration")
    if family == "FLEX_LOAD":
        if candidate["generation_type"] not in {"wind", "solar"}:
            raise ValueError("action renewable generation_type must be wind or solar")
    else:
        if not str(candidate["source_asset_id"]).strip() or not str(candidate["replacement_asset_id"]).strip():
            raise ValueError("redispatch source and replacement asset IDs are required")
        for field in (
            "source_down_headroom_mw", "replacement_up_headroom_mw",
            "source_ramp_limit_mw", "replacement_ramp_limit_mw",
        ):
            _positive_finite(candidate, field)


def _scale_allocations(
    allocations: dict[str, float],
    candidates: dict[str, Mapping[str, Any]],
    limits: dict[Any, float],
    key_fn,
) -> None:
    """Scale allocations in-place so actions sharing one resource do not double count it."""
    grouped: dict[Any, list[str]] = {}
    for action_id, amount in allocations.items():
        if amount <= 0:
            continue
        grouped.setdefault(key_fn(candidates[action_id]), []).append(action_id)
    for key, action_ids in grouped.items():
        limit = max(0.0, float(limits.get(key, 0.0)))
        total = sum(allocations[action_id] for action_id in action_ids)
        if total > limit + 1e-9 and total > 0:
            scale = limit / total
            for action_id in action_ids:
                allocations[action_id] *= scale


def screen_action_bundles(
    case: NetworkCase,
    forecast_rows: list[dict[str, Any]],
    reviewed_crosswalk: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    bundles: list[Mapping[str, Any]],
    *,
    planned_outage: Asset = DEFAULT_PLANNED_OUTAGE,
    selected_contingency: Asset | None = None,
) -> dict[str, Any]:
    """Simulate heterogeneous planning-supported action bundles on one grid state.

    FLEX_LOAD receives the bounded renewable-capture credit because it explicitly
    pairs recovered renewable output with flexible demand. GENERATOR_REDISPATCH
    changes nodal injections while preserving total MW balance and receives zero
    renewable-energy credit by itself. Its value can therefore emerge only when
    the combined network state makes a capture action feasible or safer.
    """
    validate_forecast_rows(forecast_rows)
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError(f"at most {MAX_CANDIDATES} controlled actions are supported")
    if any(not isinstance(candidate, Mapping) for candidate in candidates):
        raise ValueError("every action candidate must be an object")
    for candidate in candidates:
        _bundle_candidate_fields(candidate)
    candidate_by_id = {str(candidate["action_id"]): candidate for candidate in candidates}
    if len(candidate_by_id) != len(candidates):
        raise ValueError("action IDs must be unique")

    active_buses = {int(bus["bus_id"]) for bus in case.buses if bus["in_service"]}
    generator_buses = {
        int(generator["bus_id"])
        for generator in case.generators
        if generator.get("in_service")
    }
    generator_pmax_by_bus: dict[int, float] = {}
    for generator in case.generators:
        if not generator.get("in_service"):
            continue
        bus_id = int(generator["bus_id"])
        generator_pmax_by_bus[bus_id] = (
            generator_pmax_by_bus.get(bus_id, 0.0)
            + max(0.0, float(generator.get("pmax_mw", generator.get("pg_mw", 0.0))))
        )
    shares = normalized_load_shares(case)
    groups, mapping_confidence = reviewed_generation_groups(case, reviewed_crosswalk)

    outage_assets = (
        case.branches if planned_outage.asset_type == "branch"
        else case.transformers if planned_outage.asset_type == "transformer"
        else None
    )
    outage_id_field = "asset_id" if planned_outage.asset_type == "branch" else "transformer_id"
    if outage_assets is None or not any(
        item[outage_id_field] == planned_outage.asset_id and item["in_service"]
        for item in outage_assets
    ):
        raise ValueError("planned outage must identify an in-service case asset")
    disabled = (
        {"disabled_branches": [planned_outage.asset_id]}
        if planned_outage.asset_type == "branch"
        else {"disabled_transformers": [planned_outage.asset_id]}
    )
    n1_disabled = dict(disabled)
    if selected_contingency is not None:
        if selected_contingency == planned_outage:
            raise ValueError("selected contingency must differ from the planned outage")
        if selected_contingency.asset_type == "branch":
            n1_disabled["disabled_branches"] = [
                *n1_disabled.get("disabled_branches", []), selected_contingency.asset_id,
            ]
        elif selected_contingency.asset_type == "transformer":
            n1_disabled["disabled_transformers"] = [
                *n1_disabled.get("disabled_transformers", []), selected_contingency.asset_id,
            ]
        else:
            raise ValueError("selected contingency asset type is unsupported")

    candidate_bus_mec: dict[str, float] = {}
    for action_id, candidate in candidate_by_id.items():
        family = _candidate_family(candidate)
        if family == "FLEX_LOAD":
            load_bus = int(candidate["load_bus_id"])
            renewable_bus = int(candidate["renewable_bus_id"])
            if load_bus not in active_buses or renewable_bus not in active_buses or load_bus == renewable_bus:
                raise ValueError("flex-load action buses must be distinct active buses")
            region = str(candidate["allocation_region"]).strip()
            kind = str(candidate["generation_type"])
            sites = groups.get((region, kind), [])
            bus_mec = sum(site["mec_mw"] for site in sites if site["bus_id"] == renewable_bus)
            if bus_mec <= 0:
                raise ValueError("action renewable bus lacks a reviewed region/technology match")
            candidate_bus_mec[action_id] = bus_mec
        elif family == "GENERATOR_REDISPATCH":
            source_bus = int(candidate["source_bus_id"])
            replacement_bus = int(candidate["replacement_bus_id"])
            if (
                source_bus not in active_buses or replacement_bus not in active_buses
                or source_bus == replacement_bus
            ):
                raise ValueError("redispatch buses must be distinct active buses")
            if source_bus not in generator_buses or replacement_bus not in generator_buses:
                raise ValueError("redispatch buses must each contain an in-service case generator")

    evaluations = []
    for bundle in bundles:
        bundle_id = str(bundle["bundle_id"])
        action_ids = [str(item) for item in bundle.get("action_instance_ids", [])]
        if not action_ids:
            raise ValueError("network bundle screen accepts non-baseline bundles only")
        unknown_ids = sorted(set(action_ids) - set(candidate_by_id))
        if unknown_ids:
            raise ValueError(f"bundle references unknown action IDs: {unknown_ids}")
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("bundle action IDs must be unique")

        bundle_candidates = {action_id: candidate_by_id[action_id] for action_id in action_ids}
        intervals = []
        for row in forecast_rows:
            valid = _parse_time(str(row["valid_time"]))
            injections, dc_overrides, _ = future_injection_adapter(
                case, row, load_shares=shares, generation_groups=groups,
            )
            base_renewable, _ = allocate_regional_generation(
                row.get("regional_generation_mw", {}), groups,
            )

            flex_allocations: dict[str, float] = {}
            redispatch_allocations: dict[str, float] = {}
            bus_limits: dict[int, float] = {}
            region_limits: dict[tuple[str, str], float] = {}
            for action_id, candidate in bundle_candidates.items():
                start = _parse_time(str(candidate["available_from"]))
                end = _parse_time(str(candidate["available_until"]))
                if not start <= valid < end:
                    if _candidate_family(candidate) == "FLEX_LOAD":
                        flex_allocations[action_id] = 0.0
                    else:
                        redispatch_allocations[action_id] = 0.0
                    continue

                family = _candidate_family(candidate)
                if family == "FLEX_LOAD":
                    renewable_bus = int(candidate["renewable_bus_id"])
                    region = str(candidate["allocation_region"]).strip()
                    kind = str(candidate["generation_type"])
                    bus_limits[renewable_bus] = max(
                        0.0,
                        candidate_bus_mec[action_id] - base_renewable.get(renewable_bus, 0.0),
                    )
                    region_limits[(region, kind)] = _recoverable_mw(row, region, kind)
                    flex_allocations[action_id] = float(candidate["power_mw"])
                else:
                    source_bus = int(candidate["source_bus_id"])
                    replacement_bus = int(candidate["replacement_bus_id"])
                    demand_mw = float(row["demand_mw"])
                    source_generation = max(
                        0.0,
                        injections[source_bus]
                        + demand_mw * float(shares.get(source_bus, 0.0))
                        - base_renewable.get(source_bus, 0.0),
                    )
                    replacement_generation = max(
                        0.0,
                        injections[replacement_bus]
                        + demand_mw * float(shares.get(replacement_bus, 0.0))
                        - base_renewable.get(replacement_bus, 0.0),
                    )
                    modeled_replacement_headroom = max(
                        0.0,
                        generator_pmax_by_bus.get(replacement_bus, 0.0)
                        - replacement_generation,
                    )
                    redispatch_allocations[action_id] = min(
                        float(candidate["power_mw"]),
                        float(candidate["source_down_headroom_mw"]),
                        float(candidate["replacement_up_headroom_mw"]),
                        float(candidate["source_ramp_limit_mw"]),
                        float(candidate["replacement_ramp_limit_mw"]),
                        source_generation,
                        modeled_replacement_headroom,
                    )

            # Renewable recovery actions share the same physical opportunity.
            _scale_allocations(
                flex_allocations, bundle_candidates, bus_limits,
                lambda candidate: int(candidate["renewable_bus_id"]),
            )
            _scale_allocations(
                flex_allocations, bundle_candidates, region_limits,
                lambda candidate: (
                    str(candidate["allocation_region"]).strip(),
                    str(candidate["generation_type"]),
                ),
            )
            renewable_capture_mw = sum(flex_allocations.values())
            national_cap_mw = max(0.0, float(row["expected_constraint_mwh"]) / 0.5)
            if renewable_capture_mw > national_cap_mw + 1e-9 and renewable_capture_mw > 0:
                scale = national_cap_mw / renewable_capture_mw
                flex_allocations = {
                    action_id: amount * scale
                    for action_id, amount in flex_allocations.items()
                }
                renewable_capture_mw = national_cap_mw

            allocations = {**flex_allocations, **redispatch_allocations}
            total_action_mw = sum(allocations.values())
            if total_action_mw <= 1e-8:
                intervals.append({
                    "valid_time": row["valid_time"],
                    "applied_mw": 0.0,
                    "renewable_capture_mw": 0.0,
                    "modeled_capture_upper_bound_mwh": 0.0,
                    "action_allocations_mw": allocations,
                    "safety": None,
                    "reason": "No action capacity is available in this interval.",
                })
                continue

            changed = dict(injections)
            for action_id, amount in allocations.items():
                if amount <= 0:
                    continue
                candidate = bundle_candidates[action_id]
                family = _candidate_family(candidate)
                if family == "FLEX_LOAD":
                    changed[int(candidate["renewable_bus_id"])] += amount
                    changed[int(candidate["load_bus_id"])] -= amount
                else:
                    changed[int(candidate["source_bus_id"])] -= amount
                    changed[int(candidate["replacement_bus_id"])] += amount

            base_solve = solve_dc_case(
                case, injection_overrides_mw=injections,
                dc_transfer_overrides_mw=dc_overrides, **disabled,
            )
            solve = solve_dc_case(
                case, injection_overrides_mw=changed,
                dc_transfer_overrides_mw=dc_overrides, **disabled,
            )
            n1_base = n1_action = None
            if selected_contingency is not None:
                n1_base = solve_dc_case(
                    case, injection_overrides_mw=injections,
                    dc_transfer_overrides_mw=dc_overrides, **n1_disabled,
                )
                n1_action = solve_dc_case(
                    case, injection_overrides_mw=changed,
                    dc_transfer_overrides_mw=dc_overrides, **n1_disabled,
                )

            planned_safety = evaluate_safety(solve).to_dict()
            n1_safety = evaluate_safety(n1_action).to_dict() if n1_action is not None else None
            transmission_family = evaluate_transmission_family(
                base_solve,
                solve,
                base_contingency_solve=n1_base,
                action_contingency_solve=n1_action,
            ).to_dict()
            has_assumption = any(
                candidate["review_status"] == "scenario_assumption"
                for candidate in bundle_candidates.values()
            )
            overall = combine_checks({
                "planned_outage": CheckResult(planned_safety["overall"], "scenario result"),
                "transmission_family": CheckResult(
                    transmission_family["overall"], "family-level transmission result"
                ),
                **({"selected_n_minus_one": CheckResult(n1_safety["overall"], "scenario result")}
                   if n1_safety is not None else {}),
                **({"action_location": CheckResult("UNKNOWN", "One or more action locations are scenario assumptions")}
                   if has_assumption else {}),
            })
            intervals.append({
                "valid_time": row["valid_time"],
                "applied_mw": total_action_mw,
                "renewable_capture_mw": renewable_capture_mw,
                "modeled_capture_upper_bound_mwh": renewable_capture_mw * 0.5,
                "action_allocations_mw": allocations,
                "action_families": {
                    action_id: _candidate_family(candidate)
                    for action_id, candidate in bundle_candidates.items()
                },
                "safety": {
                    "overall": overall,
                    "planned_outage": planned_safety,
                    "selected_n_minus_one": n1_safety,
                    "families": {"transmission": transmission_family},
                },
                "network_effect": {
                    "planned_outage": {
                        "asset_id": planned_outage.asset_id,
                        "base": _network_features(base_solve),
                        "with_action": _network_features(solve),
                        "flow_changes": _flow_changes(base_solve, solve),
                    },
                    "selected_n_minus_one": (
                        {
                            "asset_id": selected_contingency.asset_id,
                            "base": _network_features(n1_base),
                            "with_action": _network_features(n1_action),
                            "flow_changes": _flow_changes(n1_base, n1_action),
                        }
                        if n1_base is not None and n1_action is not None else None
                    ),
                },
            })

        checked = [item for item in intervals if item["safety"] is not None]
        overall = (
            combine_checks({
                str(index): CheckResult(item["safety"]["overall"], "interval result")
                for index, item in enumerate(checked)
            })
            if checked else "UNKNOWN"
        )
        evaluations.append({
            "bundle_id": bundle_id,
            "action_instance_ids": action_ids,
            "contract_action_ids": [
                _candidate_family(bundle_candidates[action_id])
                for action_id in action_ids
            ],
            "safety_overall": overall,
            "modeled_capture_upper_bound_mwh": sum(
                item["modeled_capture_upper_bound_mwh"] for item in intervals
            ),
            "expected_avoided_dispatch_down_mwh": None,
            "renewable_mapping_confidence": mapping_confidence,
            "intervals": intervals,
        })

    ranked = sorted(
        (row for row in evaluations if row["safety_overall"] == "PASS"),
        key=lambda row: (-row["modeled_capture_upper_bound_mwh"], row["bundle_id"]),
    )
    return {
        "evaluated": evaluations,
        "ranked_screening_pass_bundles": [row["bundle_id"] for row in ranked],
        "best_screening_pass_bundle": ranked[0]["bundle_id"] if ranked else None,
        "recommendation": None,
        "recommendation_reason": (
            "Bundle ranking is a modeled capture screen only; expected avoided dispatch-down is not validated."
        ),
    }

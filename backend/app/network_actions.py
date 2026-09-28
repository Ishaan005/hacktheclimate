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
from backend.app.safety import CheckResult, combine_checks, evaluate_safety

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
    if candidate["review_status"] not in {"accepted_proxy", "accepted_verified"}:
        raise ValueError("action location needs an accepted review status")
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


def screen_actions(
    case: NetworkCase,
    forecast_rows: list[dict[str, Any]],
    reviewed_crosswalk: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    planned_outage: Asset = DEFAULT_PLANNED_OUTAGE,
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
        site = next((site for site in sites if site["bus_id"] == renewable_bus), None)
        if site is None:
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
            bus_headroom = max(0.0, site["mec_mw"] - base_renewable.get(renewable_bus, 0.0))
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
            # SNSP changes when renewable production and demand change. The
            # current national forecast supplies no validated action formula.
            safety = evaluate_safety(solve).to_dict()
            intervals.append({
                "valid_time": row["valid_time"], "applied_mw": applied,
                "modeled_capture_upper_bound_mwh": applied * 0.5,
                "safety": safety,
                "network_effect": {
                    "planned_outage": planned_outage.asset_id,
                    "base": _network_features(base_solve),
                    "with_action": _network_features(solve),
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

"""Self-contained golden-path planning demo.

This module deliberately packages a tiny synthetic four-bus planning case so a
fresh clone can demonstrate the real network solver, action contracts and
bundle search without the external TYTFS working files.

The operating conditions, asset names and dispatch-down outcome are synthetic.
DC flows and bundle network effects are calculated at runtime by the same
backend functions used by the planning path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .decision import generate_action_bundles, resolve_action_ids
from .network import NetworkCase, solve_dc_case
from .network_actions import screen_action_bundles
from .network_forecast import (
    _network_features,
    future_injection_adapter,
    normalized_load_shares,
    reviewed_generation_groups,
)
from .network_scenarios import Asset
from .safety import evaluate_safety

DEMO_PLANNED_OUTAGE = Asset("branch", "1:3:1")
DEMO_FURTHER_CONTINGENCY = Asset("branch", "3:4:1")
DEMO_SOURCE = "synthetic golden-path demo v1"
DEMO_BASELINE_DISPATCH_DOWN_MWH = 40.0


def matches_west_outage_demo(case: Mapping[str, Any]) -> bool:
    """Keep demo routing explicit: a normal West case must not silently use it."""
    text = str(case.get("originalText", "")).casefold()
    return "ballylickey" in text and "outage" in text


def _next_half_hour(now: datetime) -> datetime:
    now = now.astimezone(timezone.utc).replace(second=0, microsecond=0)
    floor = now.replace(minute=0 if now.minute < 30 else 30)
    return floor + timedelta(minutes=30)


def demo_network_case() -> NetworkCase:
    """Four-bus synthetic West/East system with one planned-outage bottleneck."""
    buses = [
        {"bus_id": 1, "name": "EAST GEN", "base_kv": 220.0, "bus_type": 3, "in_service": True, "vm_pu": 1.0, "va_deg": 0.0},
        {"bus_id": 2, "name": "BALLYLICKEY WIND", "base_kv": 110.0, "bus_type": 1, "in_service": True, "vm_pu": 1.0, "va_deg": 0.0},
        {"bus_id": 3, "name": "WEST FLEX", "base_kv": 110.0, "bus_type": 1, "in_service": True, "vm_pu": 1.0, "va_deg": 0.0},
        {"bus_id": 4, "name": "EAST LOAD", "base_kv": 220.0, "bus_type": 1, "in_service": True, "vm_pu": 1.0, "va_deg": 0.0},
    ]
    branches = [
        {"asset_id": "1:4:1", "from_bus": 1, "to_bus": 4, "circuit_id": "1", "r_pu": 0.0, "x_pu": 0.1, "rate_a_mva": 200.0, "rate_b_mva": 200.0, "rate_c_mva": 200.0, "in_service": True},
        {"asset_id": "2:3:1", "from_bus": 2, "to_bus": 3, "circuit_id": "1", "r_pu": 0.0, "x_pu": 0.1, "rate_a_mva": 200.0, "rate_b_mva": 200.0, "rate_c_mva": 200.0, "in_service": True},
        # Remaining West export path after 1:3:1 is out. Baseline = 60 MW
        # on a 55 MVA rate-A proxy; redispatch reduces it to 45 MW.
        {"asset_id": "3:4:1", "from_bus": 3, "to_bus": 4, "circuit_id": "1", "r_pu": 0.0, "x_pu": 0.1, "rate_a_mva": 55.0, "rate_b_mva": 65.0, "rate_c_mva": 70.0, "in_service": True},
        {"asset_id": "1:3:1", "from_bus": 1, "to_bus": 3, "circuit_id": "1", "r_pu": 0.0, "x_pu": 0.1, "rate_a_mva": 200.0, "rate_b_mva": 200.0, "rate_c_mva": 200.0, "in_service": True},
    ]
    generators = [
        {"bus_id": 1, "generator_id": "EAST-GEN", "pg_mw": 30.0, "pmax_mw": 120.0, "pmin_mw": 0.0, "in_service": True},
        {"bus_id": 3, "generator_id": "WEST-GEN", "pg_mw": 20.0, "pmax_mw": 80.0, "pmin_mw": 0.0, "in_service": True},
    ]
    loads = [
        {"bus_id": 3, "load_id": "WEST-FLEX-BASE", "p_mw": 10.0, "in_service": True},
        {"bus_id": 4, "load_id": "EAST-DEMAND", "p_mw": 90.0, "in_service": True},
    ]
    return NetworkCase(
        buses=buses,
        branches=branches,
        transformers=[],
        generators=generators,
        loads=loads,
        metadata={
            "base_mva": 100.0,
            "scenario_label": "Synthetic West outage golden-path planning case",
            "source_note": (
                "Hackathon demo case. Operating conditions and asset names are invented; "
                "network effects are computed with the DC planning solver."
            ),
            "external_dc_boundary_bus_ids": [],
        },
        dc_lines=[],
    )


def demo_crosswalk() -> list[dict[str, Any]]:
    return [{
        "allocation_region": "West Demo",
        "generation_type": "wind",
        "bus_id": 2,
        "mec_mw": 100.0,
        "review_status": "accepted_verified",
        "connection_status": "connected",
        "source": "synthetic golden-path demo",
    }]


def demo_forecast_rows(now: datetime | None = None) -> list[dict[str, Any]]:
    """48 relative half-hours; the first two hours are the constrained window."""
    decision_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = _next_half_hour(decision_time)
    issue = start - timedelta(minutes=30)
    rows: list[dict[str, Any]] = []
    for index in range(48):
        active = index < 4
        valid = start + timedelta(minutes=30 * index)
        rows.append({
            "issue_time": issue.isoformat().replace("+00:00", "Z"),
            "forecast_source": DEMO_SOURCE,
            "valid_time": valid.isoformat().replace("+00:00", "Z"),
            "constraint_probability": 0.85 if active else 0.10,
            "expected_constraint_mwh": 10.0 if active else 0.0,
            "expected_curtailment_mwh": 0.0,
            "forecast_confidence": 0.80,
            "demand_mw": 100.0,
            "regional_generation_mw": {
                "West Demo": {"wind": 50.0 if active else 35.0},
            },
            "recoverable_renewable_mw": {
                "West Demo": {"wind": 10.0 if active else 0.0},
            },
            "snsp_pct": 60.0,
            "dc_transfers_mw": {},
            "drivers": [
                "synthetic high West wind" if active else "synthetic normal conditions",
            ],
            "planned_outage_driver": "synthetic West export circuit 1:3:1 out of service",
        })
    return rows


def demo_action_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = str(rows[0]["valid_time"])
    end = str(rows[4]["valid_time"])
    return [
        {
            "action_id": "demo-flex-10",
            "contract_action_id": "FLEX_LOAD",
            "load_bus_id": 3,
            "renewable_bus_id": 2,
            "allocation_region": "West Demo",
            "generation_type": "wind",
            "power_mw": 10.0,
            "available_from": start,
            "available_until": end,
            "review_status": "scenario_assumption",
            "evidence_reference": (
                "Synthetic demo assumption: 10 MW flexible demand at West Flex node."
            ),
        },
        {
            "action_id": "demo-redispatch-15",
            "contract_action_id": "GENERATOR_REDISPATCH",
            "source_asset_id": "WEST-GEN",
            "replacement_asset_id": "EAST-GEN",
            "source_bus_id": 3,
            "replacement_bus_id": 1,
            "power_mw": 15.0,
            "source_down_headroom_mw": 20.0,
            "replacement_up_headroom_mw": 90.0,
            "source_ramp_limit_mw": 20.0,
            "replacement_ramp_limit_mw": 20.0,
            "available_from": start,
            "available_until": end,
            "review_status": "scenario_assumption",
            "evidence_reference": (
                "Synthetic demo assumption: paired 15 MW West-to-East redispatch."
            ),
        },
    ]


def _baseline_peak(
    network_case: NetworkCase,
    rows: list[dict[str, Any]],
    crosswalk: list[dict[str, Any]],
) -> dict[str, Any]:
    shares = normalized_load_shares(network_case)
    groups, _ = reviewed_generation_groups(network_case, crosswalk)
    peak: dict[str, Any] | None = None
    for row in rows[:4]:
        injections, dc_overrides, _ = future_injection_adapter(
            network_case,
            row,
            load_shares=shares,
            generation_groups=groups,
        )
        solve = solve_dc_case(
            network_case,
            injection_overrides_mw=injections,
            dc_transfer_overrides_mw=dc_overrides,
            disabled_branches=[DEMO_PLANNED_OUTAGE.asset_id],
        )
        features = _network_features(solve)
        safety = evaluate_safety(solve, snsp_pct=row["snsp_pct"]).to_dict()
        candidate = {
            "valid_time": row["valid_time"],
            "features": features,
            "safety": safety,
        }
        if peak is None or (
            features["max_dc_loading_proxy_pct"] or -1.0
        ) > (peak["features"]["max_dc_loading_proxy_pct"] or -1.0):
            peak = candidate
    if peak is None:
        raise ValueError("demo baseline produced no event interval")
    return peak


def _bundle_network_gate(bundle: Mapping[str, Any], *, require_n_minus_one: bool) -> bool:
    checked = [item for item in bundle["intervals"] if item.get("safety") is not None]
    if not checked:
        return False
    for interval in checked:
        planned = interval["safety"]["planned_outage"]
        if planned["thermal"]["status"] != "PASS" or planned["islanding"]["status"] != "PASS":
            return False
        if require_n_minus_one:
            n1 = interval["safety"].get("selected_n_minus_one")
            if (
                n1 is None
                or n1["thermal"]["status"] != "PASS"
                or n1["islanding"]["status"] != "PASS"
            ):
                return False
    return True


def _fallback_action_times(rows: list[dict[str, Any]]) -> tuple[str, str, str, str]:
    start = str(rows[0]["valid_time"])
    target = (
        datetime.fromisoformat(start.replace("Z", "+00:00")) + timedelta(minutes=15)
    ).isoformat().replace("+00:00", "Z")
    end = str(rows[4]["valid_time"])
    issue = str(rows[0]["issue_time"])
    return issue, start, target, end


def _workspace_result(
    case: Mapping[str, Any],
    scenario_ids: list[str],
    *,
    rows: list[dict[str, Any]],
    baseline_peak: Mapping[str, Any],
    selected: Mapping[str, Any] | None,
    selected_bundle_id: str | None,
    fallback: bool = False,
) -> dict[str, Any]:
    issue, start, target, end = _fallback_action_times(rows)
    baseline_loading = float(baseline_peak["features"]["max_dc_loading_proxy_pct"])
    baseline_asset = str(baseline_peak["features"]["worst_asset"])
    baseline_status = (
        "breach"
        if baseline_peak["safety"]["thermal"]["status"] == "FAIL"
        else "within_modelled_limit"
        if baseline_peak["safety"]["thermal"]["status"] == "PASS"
        else "unknown"
    )
    area_fact = case.get("facts", {}).get("affected_area", {})
    location = (
        str(area_fact.get("value"))
        if isinstance(area_fact, Mapping) and area_fact.get("value") is not None
        else "West demo area"
    )

    if selected is None:
        t4 = "T4" in scenario_ids
        reason = (
            "No modeled candidate survives the further-contingency screen: with the "
            "planned outage already applied, losing the remaining West export path "
            "islands the synthetic West area."
            if t4 else
            "No modeled candidate clears the supported network screen."
        )
        return {
            "id": str(case.get("id", "demo-west-outage")),
            "title": f"West outage golden-path demo — {' + '.join(scenario_ids)}",
            "intervalStart": start,
            "intervalEnd": end,
            "source": "demo",
            "modelRunAt": issue,
            "summary": (
                "Synthetic operating case evaluated by the real DC network and bundle "
                "engine. No candidate is promoted when the modeled network gate fails."
            ),
            "keywords": ["west", "outage", "ballylickey", "wind", "thermal"],
            "binding": {
                "type": "Transmission line",
                "metric": f"{baseline_asset} · {baseline_loading:.1f}% of rate A",
                "location": location,
                "margin": f"{55.0 - 60.0:+.1f} MW to rate A",
                "status": baseline_status,
            },
            "action": None,
            "actionPresentation": "modeled_candidate",
            "noActionReason": reason,
            "baseline": {
                "securityResult": baseline_status,
                "dispatchDownWasteMwh": DEMO_BASELINE_DISPATCH_DOWN_MWH,
            },
            "postAction": None,
            "impact": None,
            "guardrails": [
                {
                    "name": "transmission_line",
                    "baseline": baseline_status,
                    "postAction": "unknown",
                    "margin": "-5.0 MW",
                    "timestamp": str(baseline_peak["valid_time"]),
                    "note": "Computed on the synthetic DC planning network.",
                },
                {
                    "name": "thermal_capacity",
                    "baseline": "unknown",
                    "postAction": "unknown",
                    "margin": None,
                    "timestamp": None,
                    "note": "The compact demo contains no transformer thermal model.",
                },
                {
                    "name": "snsp",
                    "baseline": "within_modelled_limit",
                    "postAction": "unknown",
                    "margin": "15 pp",
                    "timestamp": str(baseline_peak["valid_time"]),
                    "note": "60% synthetic baseline versus the 75% demo threshold; action SNSP is not recalculated.",
                },
                {
                    "name": "scope",
                    "baseline": "unknown",
                    "postAction": "unknown",
                    "margin": None,
                    "timestamp": None,
                    "note": "Synthetic four-bus case; not a live locational model.",
                },
                {
                    "name": "min_generation",
                    "baseline": "unknown",
                    "postAction": "unknown",
                    "margin": None,
                    "timestamp": None,
                    "note": "Minimum-unit evidence is outside this compact demo.",
                },
            ],
        }

    active_intervals = [
        item for item in selected["intervals"]
        if item.get("safety") is not None
    ]
    peak_post = max(
        active_intervals,
        key=lambda item: item["network_effect"]["planned_outage"]["with_action"][
            "max_dc_loading_proxy_pct"
        ] or -1.0,
    )
    post_features = peak_post["network_effect"]["planned_outage"]["with_action"]
    post_loading = float(post_features["max_dc_loading_proxy_pct"])
    capture = float(selected["modeled_capture_upper_bound_mwh"])
    assumed_post_dispatch_down = max(0.0, DEMO_BASELINE_DISPATCH_DOWN_MWH - capture)

    summary_suffix = (
        " A precomputed fallback view is being shown."
        if fallback else ""
    )
    return {
        "id": str(case.get("id", "demo-west-outage")),
        "title": f"West outage golden-path demo — {' + '.join(scenario_ids)}",
        "intervalStart": start,
        "intervalEnd": end,
        "source": "demo",
        "modelRunAt": issue,
        "summary": (
            "Synthetic operating conditions; the DC network effect and action-bundle "
            "search are calculated by the real backend. The dispatch-down outcome uses "
            "the modeled renewable-capture upper bound as a demo assumption, not a "
            f"validated avoided-dispatch-down forecast.{summary_suffix}"
        ),
        "keywords": ["west", "outage", "ballylickey", "wind", "thermal", "bundle"],
        "binding": {
            "type": "Transmission line",
            "metric": f"{baseline_asset} · {baseline_loading:.1f}% of rate A",
            "location": location,
            "margin": "-5.0 MW to rate A",
            "status": "breach",
        },
        "action": {
            # The UI's existing family card is kept; the asset name and steps
            # make the paired bundle explicit.
            "family": "flexible_demand",
            "assetName": "10 MW flexible demand + 15 MW redispatch bundle",
            "location": "Synthetic West/East nodes",
            "currentState": "No coordinated intervention",
            "targetState": "10 MW local demand increase + 15 MW West-to-East redispatch",
            "issueTime": issue,
            "startTime": start,
            "targetTime": target,
            "effectiveUntil": end,
            "earliestExecution": start,
            "executability": "conditional",
            "steps": [
                {
                    "time": issue,
                    "text": (
                        "Demo assumption: make 10 MW of flexible demand available "
                        "inside the West area."
                    ),
                },
                {
                    "time": start,
                    "text": (
                        "Demo assumption: pair it with a 15 MW redispatch from "
                        "WEST-GEN to EAST-GEN."
                    ),
                },
                {
                    "time": target,
                    "text": (
                        f"Re-run the DC planning case: {baseline_asset} falls from "
                        f"{baseline_loading:.1f}% to {post_loading:.1f}% of rate A."
                    ),
                },
                {
                    "time": None,
                    "text": (
                        "Before any real instruction, verify asset capability, timing, "
                        "reserve, voltage and stability evidence."
                    ),
                },
            ],
            "details": {
                "direction": "increase",
                "changeMw": 10.0,
                "availableMwh": capture,
                "demandBaselineMw": 10.0,
                "activationDelayMinutes": 0,
                "maxDurationMinutes": 120,
                "constraintReliefPerMw": None,
                "reboundRequirement": "Not modeled in the golden-path case.",
                "activationCostEur": None,
                "reboundCostEur": None,
            },
        },
        "actionPresentation": "modeled_candidate",
        "noActionReason": (
            f"{selected_bundle_id} is a modeled candidate only; unsupported safety "
            "evidence remains outside the compact demo."
        ),
        "baseline": {
            "securityResult": "breach",
            "dispatchDownWasteMwh": DEMO_BASELINE_DISPATCH_DOWN_MWH,
        },
        "postAction": {
            "securityResult": "within_modelled_limit",
            "dispatchDownWasteMwh": assumed_post_dispatch_down,
        },
        "impact": {
            "grossMarketOpportunityEur": None,
            "netFinancialValueEur": None,
            "estimatedAvoidedEmissionsTco2e": None,
        },
        "guardrails": [
            {
                "name": "transmission_line",
                "baseline": "breach",
                "postAction": "within_modelled_limit",
                "margin": f"{55.0 - 45.0:+.1f} MW",
                "timestamp": str(peak_post["valid_time"]),
                "note": (
                    f"Synthetic DC result: {baseline_asset} falls from "
                    f"{baseline_loading:.1f}% to {post_loading:.1f}% of rate A."
                ),
            },
            {
                "name": "thermal_capacity",
                "baseline": "unknown",
                "postAction": "unknown",
                "margin": None,
                "timestamp": None,
                "note": "The compact demo contains no transformer thermal model.",
            },
            {
                "name": "snsp",
                "baseline": "within_modelled_limit",
                "postAction": "unknown",
                "margin": "15 pp",
                "timestamp": str(peak_post["valid_time"]),
                "note": "Action-level SNSP is intentionally left unknown.",
            },
            {
                "name": "scope",
                "baseline": "unknown",
                "postAction": "unknown",
                "margin": None,
                "timestamp": None,
                "note": "Synthetic four-bus planning case; not a live locational model.",
            },
            {
                "name": "min_generation",
                "baseline": "unknown",
                "postAction": "unknown",
                "margin": None,
                "timestamp": None,
                "note": "Minimum-unit and stability evidence are not part of this demo.",
            },
        ],
    }


def evaluate_west_outage_demo(
    case: Mapping[str, Any],
    scenario_ids: list[str],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run the golden-path case through real bundle and network calculations."""
    rows = demo_forecast_rows(now)
    network_case = demo_network_case()
    crosswalk = demo_crosswalk()
    candidates = demo_action_candidates(rows)

    # Exercise the action contract before the physical executor.
    parameters = {key for candidate in candidates for key in candidate}
    resolved = {
        item.action_id: item
        for item in resolve_action_ids(
            scenario_ids,
            available_parameters=parameters,
            available_evidence_fields={"recoverable_renewable_mw"},
        )
    }
    for family in ("FLEX_LOAD", "GENERATOR_REDISPATCH"):
        action = resolved.get(family)
        if action is None or action.eligibility != "eligible" or action.execution_status != "planning_supported":
            raise ValueError(f"demo action family {family} is not planning-supported for {scenario_ids}")

    generated = generate_action_bundles(candidates, max_bundle_size=2)
    non_baseline = [
        bundle.model_dump(mode="json")
        for bundle in generated.bundles
        if not bundle.is_baseline
    ]
    require_n1 = "T4" in scenario_ids
    screened = screen_action_bundles(
        network_case,
        rows,
        crosswalk,
        candidates,
        non_baseline,
        planned_outage=DEMO_PLANNED_OUTAGE,
        selected_contingency=DEMO_FURTHER_CONTINGENCY if require_n1 else None,
    )
    baseline_peak = _baseline_peak(network_case, rows, crosswalk)

    viable = [
        item for item in screened["evaluated"]
        if _bundle_network_gate(item, require_n_minus_one=require_n1)
    ]
    viable.sort(
        key=lambda item: (
            -float(item["modeled_capture_upper_bound_mwh"]),
            item["bundle_id"],
        )
    )
    selected = viable[0] if viable else None
    return _workspace_result(
        case,
        scenario_ids,
        rows=rows,
        baseline_peak=baseline_peak,
        selected=selected,
        selected_bundle_id=selected["bundle_id"] if selected else None,
    )


def fallback_west_outage_demo(
    case: Mapping[str, Any],
    scenario_ids: list[str],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Presentation-safe fallback using the known result from the same synthetic case."""
    rows = demo_forecast_rows(now)
    baseline_peak = {
        "valid_time": rows[0]["valid_time"],
        "features": {
            "max_dc_loading_proxy_pct": 109.0909090909,
            "worst_asset": "3:4:1",
        },
        "safety": {"thermal": {"status": "FAIL"}},
    }
    if "T4" in scenario_ids:
        return _workspace_result(
            case,
            scenario_ids,
            rows=rows,
            baseline_peak=baseline_peak,
            selected=None,
            selected_bundle_id=None,
            fallback=True,
        )
    selected = {
        "bundle_id": "BUNDLE:demo-flex-10+demo-redispatch-15",
        "modeled_capture_upper_bound_mwh": 20.0,
        "intervals": [{
            "valid_time": rows[0]["valid_time"],
            "safety": {"planned_outage": {"thermal": {"status": "PASS"}, "islanding": {"status": "PASS"}}},
            "network_effect": {
                "planned_outage": {
                    "with_action": {
                        "max_dc_loading_proxy_pct": 81.8181818182,
                        "worst_asset": "3:4:1",
                    }
                }
            },
        }],
    }
    return _workspace_result(
        case,
        scenario_ids,
        rows=rows,
        baseline_peak=baseline_peak,
        selected=selected,
        selected_bundle_id=selected["bundle_id"],
        fallback=True,
    )

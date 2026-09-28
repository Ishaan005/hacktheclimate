"""Compare reviewed topology changes in a static DC planning case."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.app.network import solve_dc_case

ISLAND_SECURITY_REASON = (
    "Islanded contingency detected; a disconnected AC state needs a separate "
    "balancing and operability review. Branch flows are suppressed."
)


@dataclass(frozen=True)
class Asset:
    asset_type: str
    asset_id: str

    def __post_init__(self) -> None:
        if self.asset_type not in {"branch", "transformer"}:
            raise ValueError("asset_type must be branch or transformer")
        if not self.asset_id:
            raise ValueError("asset_id is required")


def _flow_key(flow: Mapping[str, Any]) -> tuple[str, str]:
    return str(flow["asset_type"]), str(flow["asset_id"])


def _active_case_asset(case: Any, asset: Asset) -> bool:
    if asset.asset_type == "branch":
        return any(
            row["asset_id"] == asset.asset_id and row["in_service"]
            for row in case.branches
        )
    return any(
        row["in_service"]
        and (
            row["transformer_id"] == asset.asset_id
            or (
                row.get("third_bus")
                and asset.asset_id in {
                    row["transformer_id"] + "/w1",
                    row["transformer_id"] + "/w2",
                    row["transformer_id"] + "/w3",
                }
            )
        )
        for row in case.transformers
    )


def summarize_run(result: Mapping[str, Any]) -> dict[str, Any]:
    status = result["status"]
    security_event = status == "islanded"
    operable_state = status == "ok"
    flows = [] if security_event else sorted(result["flows"], key=_flow_key)
    reason = ISLAND_SECURITY_REASON if security_event else result.get("reason")
    return {
        "status": status,
        "reason": reason,
        "security_event": security_event,
        "operable_state": operable_state,
        "actionable": operable_state,
        "source_injection_residual_mw": result.get("balance_mw"),
        "dc_transfers_mw": dict(result.get("dc_transfers_mw", {})),
        "islands": result.get("islands", []),
        "flows": [
            {
                "asset_type": flow["asset_type"],
                "asset_id": flow["asset_id"],
                "from_bus": flow["from_bus"],
                "to_bus": flow["to_bus"],
                "flow_mw": flow["flow_mw"],
                "rating_mva": flow["rating_mva"],
                "dc_loading_pct_proxy": flow["loading_pct"],
                "dc_headroom_mw_unity_pf_proxy": (
                    flow["rating_mva"] - abs(flow["flow_mw"])
                    if flow["rating_mva"] is not None
                    else None
                ),
            }
            for flow in flows
        ],
    }


def _summarize(result: Mapping[str, Any]) -> dict[str, Any]:
    return summarize_run(result)


def _deltas(base: Mapping[str, Any], scenario: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    if base["status"] != "ok" or scenario["status"] != "ok":
        return None
    baseline = {_flow_key(flow): flow for flow in base["flows"]}
    changed = {_flow_key(flow): flow for flow in scenario["flows"]}
    deltas = []
    for key in sorted(baseline.keys() | changed.keys()):
        before = baseline.get(key)
        after = changed.get(key)
        before_headroom = before.get("dc_headroom_mw_unity_pf_proxy") if before else None
        after_headroom = after.get("dc_headroom_mw_unity_pf_proxy") if after else None
        delta_flow = after["flow_mw"] - before["flow_mw"] if before and after else None
        deltas.append(
            {
                "asset_type": key[0],
                "asset_id": key[1],
                "intact_flow_mw": before["flow_mw"] if before else None,
                "scenario_flow_mw": after["flow_mw"] if after else None,
                "delta_flow_mw": delta_flow,
                "abs_delta_flow_mw": abs(delta_flow) if delta_flow is not None else None,
                "intact_headroom_mw": before_headroom,
                "scenario_headroom_mw": after_headroom,
                "headroom_decrease_mw": (
                    before_headroom - after_headroom
                    if before_headroom is not None and after_headroom is not None
                    else None
                ),
                "state": "online" if before and after else "removed" if before else "added",
            }
        )
    return deltas


def _run_stress(run: Mapping[str, Any]) -> dict[str, Any]:
    if not run.get("operable_state"):
        return {
            "actionable": False,
            "top_10_highest_loading_proxies": [],
            "threshold_breaches": None,
            "max_dc_loading_proxy_pct": None,
            "minimum_headroom_proxy_mw": None,
            "worst_asset": None,
        }
    rated = [
        flow for flow in run["flows"]
        if flow["dc_loading_pct_proxy"] is not None
    ]
    rated.sort(key=lambda flow: (-abs(flow["dc_loading_pct_proxy"]), _flow_key(flow)))
    top = rated[:10]
    thresholds: dict[str, dict[str, Any]] = {}
    for label, threshold in (("above_80pct", 80.0), ("above_90pct", 90.0), ("above_100pct", 100.0)):
        breached = [
            {
                "asset_type": flow["asset_type"],
                "asset_id": flow["asset_id"],
                "dc_loading_pct_proxy": flow["dc_loading_pct_proxy"],
            }
            for flow in rated
            if flow["dc_loading_pct_proxy"] > threshold
        ]
        thresholds[label] = {"count": len(breached), "assets": breached}
    headrooms = [
        flow["dc_headroom_mw_unity_pf_proxy"]
        for flow in rated
        if flow["dc_headroom_mw_unity_pf_proxy"] is not None
    ]
    worst = top[0] if top else None
    return {
        "actionable": True,
        "top_10_highest_loading_proxies": [
            {
                "asset_type": flow["asset_type"],
                "asset_id": flow["asset_id"],
                "flow_mw": flow["flow_mw"],
                "rating_mva": flow["rating_mva"],
                "dc_loading_pct_proxy": flow["dc_loading_pct_proxy"],
                "dc_headroom_mw_unity_pf_proxy": flow["dc_headroom_mw_unity_pf_proxy"],
            }
            for flow in top
        ],
        "threshold_breaches": thresholds,
        "max_dc_loading_proxy_pct": worst["dc_loading_pct_proxy"] if worst else None,
        "minimum_headroom_proxy_mw": min(headrooms) if headrooms else None,
        "worst_asset": (
            {"asset_type": worst["asset_type"], "asset_id": worst["asset_id"]}
            if worst else None
        ),
    }


def _delta_stress(deltas: list[dict[str, Any]] | None) -> dict[str, Any]:
    if deltas is None:
        return {
            "actionable": False,
            "top_10_largest_headroom_decreases": [],
            "top_10_largest_absolute_flow_changes": [],
        }
    headroom = [row for row in deltas if row["headroom_decrease_mw"] is not None]
    headroom.sort(key=lambda row: (-row["headroom_decrease_mw"], row["asset_type"], row["asset_id"]))
    flow_changes = [row for row in deltas if row["abs_delta_flow_mw"] is not None]
    flow_changes.sort(key=lambda row: (-row["abs_delta_flow_mw"], row["asset_type"], row["asset_id"]))
    return {
        "actionable": True,
        "top_10_largest_headroom_decreases": headroom[:10],
        "top_10_largest_absolute_flow_changes": flow_changes[:10],
    }


def build_stress_ranking(
    runs: Mapping[str, Mapping[str, Any]],
    *,
    deltas_from_intact: Mapping[str, list[dict[str, Any]] | None],
    contingency: Asset,
) -> dict[str, Any]:
    by_run = {name: _run_stress(run) for name, run in runs.items()}
    comparisons = {
        name: _delta_stress(delta)
        for name, delta in deltas_from_intact.items()
    }
    scenario_candidates = []
    for run_name in ("planned_outage", "selected_n_minus_one"):
        stress = by_run.get(run_name)
        if stress and stress["actionable"] and stress["max_dc_loading_proxy_pct"] is not None:
            scenario_candidates.append((stress["max_dc_loading_proxy_pct"], run_name, stress))
    scenario_candidates.sort(key=lambda item: (-item[0], item[1]))
    worst_scenario = scenario_candidates[0] if scenario_candidates else None
    n1 = by_run.get("selected_n_minus_one", {})
    selected_n1_run = runs["selected_n_minus_one"]
    return {
        "runs": by_run,
        "comparisons_from_intact": comparisons,
        "worst_asset": worst_scenario[2]["worst_asset"] if worst_scenario else None,
        "most_stressed_scenario": worst_scenario[1] if worst_scenario else None,
        "worst_contingency": {
            **vars(contingency),
            "operable_state": bool(selected_n1_run.get("operable_state")),
            "security_event": bool(selected_n1_run.get("security_event")),
            "max_dc_loading_proxy_pct": n1.get("max_dc_loading_proxy_pct"),
            "worst_asset": n1.get("worst_asset"),
        },
    }


def compare_network_scenarios(
    case: Any,
    *,
    planned_outage: Asset,
    contingency: Asset,
    monitored: Asset,
    injection_overrides_mw: Mapping[int, float] | None = None,
    dc_transfer_overrides_mw: Mapping[str, float] | None = None,
    outage_reference: str,
    contingency_reference: str,
) -> dict[str, Any]:
    """Solve intact, planned outage, then that outage plus one selected N-1."""
    if not outage_reference.strip():
        raise ValueError("outage_reference is required")
    if not contingency_reference.strip():
        raise ValueError("contingency_reference is required")
    if planned_outage == contingency:
        raise ValueError("contingency must differ from the planned outage")
    if any(
        asset.asset_type == "transformer" and asset.asset_id.endswith(("/w1", "/w2", "/w3"))
        for asset in (planned_outage, contingency)
    ):
        raise ValueError("disable the parent transformer ID, not an individual winding")
    if any(
        monitored == disabled
        or (
            monitored.asset_type == disabled.asset_type == "transformer"
            and monitored.asset_id.startswith(disabled.asset_id + "/w")
        )
        for disabled in (planned_outage, contingency)
    ):
        raise ValueError("monitored asset must remain online in all scenarios")

    overrides = dict(injection_overrides_mw) if injection_overrides_mw is not None else None
    dc_overrides = dict(dc_transfer_overrides_mw) if dc_transfer_overrides_mw is not None else None

    def solve(disabled: tuple[Asset, ...]) -> dict[str, Any]:
        return solve_dc_case(
            case,
            disabled_branches=tuple(asset.asset_id for asset in disabled if asset.asset_type == "branch"),
            disabled_transformers=tuple(
                asset.asset_id for asset in disabled if asset.asset_type == "transformer"
            ),
            injection_overrides_mw=overrides,
            dc_transfer_overrides_mw=dc_overrides,
        )

    for label, asset in (
        ("planned outage", planned_outage),
        ("contingency", contingency),
        ("monitored asset", monitored),
    ):
        if not _active_case_asset(case, asset):
            raise ValueError(f"{label} is absent or out of service in the intact case: {asset}")

    intact = solve(())
    intact_flows = {_flow_key(flow): flow for flow in intact["flows"]}
    monitor_key = (monitored.asset_type, monitored.asset_id)
    if intact["status"] != "unsolved" and monitor_key not in intact_flows:
        raise ValueError("monitor a specific transformer winding ID, not its three-winding parent")

    outage = solve((planned_outage,))
    n_minus_one = solve((planned_outage, contingency))
    runs = {
        "intact": summarize_run(intact),
        "planned_outage": summarize_run(outage),
        "selected_n_minus_one": summarize_run(n_minus_one),
    }
    monitor_by_run = {
        name: next((flow for flow in run["flows"] if _flow_key(flow) == monitor_key), None)
        for name, run in runs.items()
    }
    deltas_from_intact = {
        "planned_outage": _deltas(runs["intact"], runs["planned_outage"]),
        "selected_n_minus_one": _deltas(runs["intact"], runs["selected_n_minus_one"]),
    }
    deltas_from_planned = _deltas(runs["planned_outage"], runs["selected_n_minus_one"])
    return {
        "scenario_label": "planning scenario",
        "case_type": "static TYTFS study case; approximate DC active-power flow",
        "case_provenance": dict(case.metadata),
        "injection_overrides_mw": overrides,
        "dc_transfer_overrides_mw": dc_overrides,
        "rating_basis": "TYTFS RAW rate A (MVA); active-power comparison is a DC screening proxy",
        "outage_reference": outage_reference,
        "contingency_reference": contingency_reference,
        "planned_outage": vars(planned_outage),
        "contingency": vars(contingency),
        "monitored": vars(monitored),
        "monitor_by_run": monitor_by_run,
        "runs": runs,
        "flow_deltas_from_intact": deltas_from_intact,
        "flow_deltas_from_planned_outage": deltas_from_planned,
        "stress_ranking": build_stress_ranking(
            runs,
            deltas_from_intact=deltas_from_intact,
            contingency=contingency,
        ),
        "limitations": [
            "Scheduled outage dates do not establish actual equipment state.",
            "DC flow omits voltage, reactive power, losses and dynamic behavior.",
            "MVA rating compared with active MW flow is a screening proxy, not measured thermal headroom.",
            "Islanded contingency flows are suppressed because disconnected components are not an operable balanced state.",
            "This is not an EirGrid N-1 security verdict or an actual future line-loading forecast.",
        ],
    }

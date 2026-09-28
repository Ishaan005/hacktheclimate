"""Compare a reviewed outage and one contingency in a static DC planning case."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.app.network import solve_dc_case


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


def _present_in_flows(asset: Asset, flows: Mapping[tuple[str, str], Any]) -> bool:
    key = (asset.asset_type, asset.asset_id)
    if key in flows:
        return True
    return asset.asset_type == "transformer" and any(
        asset_type == "transformer" and asset_id.startswith(asset.asset_id + "/w")
        for asset_type, asset_id in flows
    )


def _summarize(result: Mapping[str, Any]) -> dict[str, Any]:
    flows = sorted(result["flows"], key=_flow_key)
    return {
        "status": result["status"],
        "reason": result.get("reason"),
        "balance_mw": result.get("balance_mw"),
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
                "dc_headroom_mva_proxy": (
                    flow["rating_mva"] - abs(flow["flow_mw"])
                    if flow["rating_mva"] is not None
                    else None
                ),
            }
            for flow in flows
        ],
    }


def _deltas(base: Mapping[str, Any], scenario: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    if base["status"] == "unsolved" or scenario["status"] == "unsolved":
        return None
    baseline = {_flow_key(flow): flow for flow in base["flows"]}
    changed = {_flow_key(flow): flow for flow in scenario["flows"]}
    deltas = []
    for key in sorted(baseline.keys() | changed.keys()):
        before = baseline.get(key)
        after = changed.get(key)
        deltas.append(
            {
                "asset_type": key[0],
                "asset_id": key[1],
                "intact_flow_mw": before["flow_mw"] if before else None,
                "scenario_flow_mw": after["flow_mw"] if after else None,
                "delta_flow_mw": (
                    after["flow_mw"] - before["flow_mw"] if before and after else None
                ),
                "state": "online" if before and after else "removed" if before else "added",
            }
        )
    return deltas


def compare_network_scenarios(
    case: Any,
    *,
    planned_outage: Asset,
    contingency: Asset,
    monitored: Asset,
    injection_overrides_mw: Mapping[int, float] | None = None,
    outage_reference: str,
    contingency_reference: str,
) -> dict[str, Any]:
    """Solve intact, planned outage, then that outage plus one selected N-1.

    ``outage_reference`` names the reviewed match and publication so the
    simulated topology change remains traceable. All three solves use the same
    case and injections. No re-dispatch is performed between scenarios.
    """
    if not outage_reference.strip():
        raise ValueError("outage_reference is required")
    if not contingency_reference.strip():
        raise ValueError("contingency_reference is required")
    if planned_outage == contingency:
        raise ValueError("contingency must differ from the planned outage")
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

    def solve(disabled: tuple[Asset, ...]) -> dict[str, Any]:
        return solve_dc_case(
            case,
            disabled_branches=tuple(asset.asset_id for asset in disabled if asset.asset_type == "branch"),
            disabled_transformers=tuple(
                asset.asset_id for asset in disabled if asset.asset_type == "transformer"
            ),
            injection_overrides_mw=overrides,
        )

    intact = solve(())
    intact_flows = {_flow_key(flow): flow for flow in intact["flows"]}
    for label, asset in (
        ("planned outage", planned_outage),
        ("contingency", contingency),
        ("monitored asset", monitored),
    ):
        if not _present_in_flows(asset, intact_flows):
            raise ValueError(f"{label} is absent or out of service in the intact case: {asset}")
    monitor_key = (monitored.asset_type, monitored.asset_id)
    if monitor_key not in intact_flows:
        raise ValueError("monitor a specific transformer winding ID, not its three-winding parent")

    outage = solve((planned_outage,))
    n_minus_one = solve((planned_outage, contingency))
    runs = {"intact": _summarize(intact), "planned_outage": _summarize(outage), "selected_n_minus_one": _summarize(n_minus_one)}
    monitor_by_run = {
        name: next((flow for flow in run["flows"] if _flow_key(flow) == monitor_key), None)
        for name, run in runs.items()
    }
    return {
        "scenario_label": "planning scenario",
        "case_type": "static TYTFS study case; approximate DC active-power flow",
        "rating_basis": "TYTFS RAW rate A (MVA); active-power comparison is a DC screening proxy",
        "outage_reference": outage_reference,
        "contingency_reference": contingency_reference,
        "planned_outage": vars(planned_outage),
        "contingency": vars(contingency),
        "monitored": vars(monitored),
        "monitor_by_run": monitor_by_run,
        "runs": runs,
        "flow_deltas_from_intact": {
            "planned_outage": _deltas(runs["intact"], runs["planned_outage"]),
            "selected_n_minus_one": _deltas(runs["intact"], runs["selected_n_minus_one"]),
        },
        "flow_deltas_from_planned_outage": _deltas(
            runs["planned_outage"], runs["selected_n_minus_one"]
        ),
        "limitations": [
            "Scheduled outage dates do not establish actual equipment state.",
            "DC flow omits voltage, reactive power, losses and dynamic behavior.",
            "MVA rating compared with active MW flow is a screening proxy, not measured thermal headroom.",
            "This is not an EirGrid N-1 security verdict or an actual future line-loading forecast.",
        ],
    }

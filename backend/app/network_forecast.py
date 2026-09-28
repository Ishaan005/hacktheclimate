"""Forward 48-half-hour network constraint screening.

The module intentionally requires reviewed regional generator mappings and an
upstream forecast input file. It does not fabricate regional buses or future
weather. The upstream input supplies national constraint probability/expected
MWh plus future demand, regional renewables, and optional interconnector MW.
This layer turns those forecasts into nodal injections and DC network features.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.app.network import NetworkCase, load_case, solve_dc_case
from backend.app.network_scenarios import Asset
from backend.app.safety import evaluate_safety

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASE_DIR = Path(os.getenv("NETWORK_CASE_DIR", REPO_ROOT / "data/raw/network_case"))
DEFAULT_INPUT_PATH = Path(os.getenv("NETWORK_FORECAST_INPUT", REPO_ROOT / "data/processed/network_forecast_inputs.json"))
DEFAULT_CROSSWALK_PATH = Path(os.getenv("NETWORK_GENERATOR_CROSSWALK", REPO_ROOT / "data/raw/network_case/generator_crosswalk.csv"))
DEFAULT_PLANNED_OUTAGE = Asset("branch", os.getenv("NETWORK_PLANNED_OUTAGE_ID", "1642:2522:1"))


def _finite(value: Any, label: str, *, nonnegative: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number) or (nonnegative and number < 0):
        qualifier = "nonnegative finite" if nonnegative else "finite"
        raise ValueError(f"{label} must be {qualifier}")
    return number


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO 8601 time: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError("network forecast times must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_forecast_rows(
    rows: list[dict[str, Any]],
    *,
    as_of: datetime | None = None,
) -> None:
    if not isinstance(rows, list) or len(rows) != 48:
        raise ValueError("network forecast input must contain exactly 48 half-hour rows")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("each network forecast row must be an object")
    required = {
        "issue_time", "forecast_source", "valid_time", "demand_mw",
        "constraint_probability", "expected_constraint_mwh", "forecast_confidence",
    }
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"network forecast row missing fields: {sorted(missing)}")
    times = [_parse_time(str(row["valid_time"])) for row in rows]
    issue_times = [_parse_time(str(row["issue_time"])) for row in rows]
    if len(set(issue_times)) != 1 or issue_times[0] > times[0]:
        raise ValueError("48 rows must share one issue_time no later than the first valid_time")
    if any(not isinstance(row["forecast_source"], str) for row in rows):
        raise ValueError("forecast_source must be a string")
    sources = {row["forecast_source"].strip() for row in rows}
    if len(sources) != 1 or not next(iter(sources)):
        raise ValueError("48 rows must name one nonempty forecast_source")
    if any(time.minute not in (0, 30) or time.second or time.microsecond for time in times):
        raise ValueError("network forecast valid_time must align to half-hour boundaries")
    if any(later - earlier != timedelta(minutes=30) for earlier, later in zip(times, times[1:])):
        raise ValueError("network forecast valid_time values must be contiguous half-hours")
    if as_of is not None:
        if as_of.tzinfo is None:
            raise ValueError("as_of must include a UTC offset")
        as_of = as_of.astimezone(timezone.utc)
        if issue_times[0] > as_of:
            raise ValueError("network forecast issue_time is later than the request time")
        if as_of - issue_times[0] > timedelta(hours=24):
            raise ValueError("network forecast issue_time is more than 24 hours old")
        if not timedelta(0) < times[0] - as_of <= timedelta(hours=1):
            raise ValueError("network forecast must start within the next hour")
    for row in rows:
        _finite(row["demand_mw"], "demand_mw", nonnegative=True)
        _finite(row["constraint_probability"], "constraint_probability", nonnegative=True)
        _finite(row["expected_constraint_mwh"], "expected_constraint_mwh", nonnegative=True)
        confidence = _finite(row["forecast_confidence"], "forecast_confidence", nonnegative=True)
        probability = float(row["constraint_probability"])
        if probability > 1 or confidence > 1:
            raise ValueError("probability and forecast confidence must be in [0, 1]")
        if row.get("snsp_pct") is not None:
            snsp = _finite(row["snsp_pct"], "snsp_pct", nonnegative=True)
            if snsp > 100:
                raise ValueError("snsp_pct must be in [0, 100]")
        if not isinstance(row.get("regional_generation_mw", {}), Mapping):
            raise ValueError("regional_generation_mw must be an object")
        if not isinstance(row.get("recoverable_renewable_mw", {}), Mapping):
            raise ValueError("recoverable_renewable_mw must be an object")
        if not isinstance(row.get("dc_transfers_mw", {}), Mapping):
            raise ValueError("dc_transfers_mw must be an object")
        if not isinstance(row.get("drivers", []), list) or any(
            not isinstance(driver, str) for driver in row.get("drivers", [])
        ):
            raise ValueError("drivers must be a list of strings")


def load_forecast_inputs(
    path: str | Path,
    *,
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    rows = json.loads(Path(path).read_text())
    validate_forecast_rows(rows, as_of=as_of)
    return rows


def load_reviewed_crosswalk(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = {"allocation_region", "generation_type", "bus_id", "mec_mw", "review_status"}
    if not rows or not required <= set(rows[0]):
        raise ValueError("generator crosswalk is empty or missing reviewed allocation fields")
    accepted = []
    for row in rows:
        if row.get("connection_status", "connected").strip().lower() != "connected":
            continue
        if row["review_status"].strip() not in {"accepted_proxy", "accepted_verified"}:
            continue
        accepted.append({
            **row,
            "bus_id": int(row["bus_id"]),
            "mec_mw": _finite(row["mec_mw"], "crosswalk MEC", nonnegative=True),
        })
    if not accepted:
        raise ValueError("generator crosswalk contains no reviewed connected mappings")
    return accepted


def normalized_load_shares(case: NetworkCase) -> dict[int, float]:
    by_bus: dict[int, float] = defaultdict(float)
    for load in case.loads:
        if not load["in_service"]:
            continue
        mw = _finite(load["p_mw"], f"load at bus {load['bus_id']}")
        if mw < 0:
            raise ValueError("negative RAW loads require an explicit treatment before nodal scaling")
        by_bus[int(load["bus_id"])] += mw
    total = sum(by_bus.values())
    if total <= 0:
        raise ValueError("case has no positive in-service load for nodal scaling")
    return {bus: mw / total for bus, mw in by_bus.items()}


def _kind(value: str) -> str:
    value = value.strip().lower()
    return "wind" if value == "offshore wind" else value


def reviewed_generation_groups(
    case: NetworkCase,
    crosswalk: Iterable[Mapping[str, Any]],
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], str]:
    active_buses = {int(bus["bus_id"]) for bus in case.buses if bus["in_service"]}
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    confidence = "high"
    for row in crosswalk:
        kind = _kind(str(row["generation_type"]))
        if kind not in {"wind", "solar"}:
            continue
        bus_id = int(row["bus_id"])
        if bus_id not in active_buses:
            raise ValueError(f"reviewed generator bus {bus_id} is not active in the case")
        status = str(row["review_status"]).strip()
        if status not in {"accepted_proxy", "accepted_verified"}:
            continue
        if status == "accepted_proxy":
            confidence = "medium"
        groups[(str(row["allocation_region"]).strip(), kind)].append({
            "bus_id": bus_id,
            "mec_mw": _finite(row["mec_mw"], f"MEC for bus {bus_id}", nonnegative=True),
            "review_status": status,
        })
    if not groups:
        raise ValueError("no reviewed wind/solar groups are available")
    return groups, confidence


def allocate_regional_generation(
    regional_generation_mw: Mapping[str, Any],
    groups: Mapping[tuple[str, str], list[dict[str, Any]]],
) -> tuple[dict[int, float], dict[str, float]]:
    by_bus: dict[int, float] = defaultdict(float)
    totals = {"wind": 0.0, "solar": 0.0}
    for region, kinds in regional_generation_mw.items():
        if not isinstance(kinds, Mapping):
            raise ValueError(f"regional generation for {region} must be an object")
        for kind_raw, value in kinds.items():
            kind = _kind(str(kind_raw))
            if kind not in totals:
                raise ValueError("only wind and solar are accepted in regional_generation_mw")
            forecast_mw = _finite(value, f"{region} {kind} forecast", nonnegative=True)
            if forecast_mw == 0:
                continue
            key = (str(region), kind)
            sites = groups.get(key, [])
            if not sites:
                raise ValueError(f"forecast group {key} has no reviewed connected generator mapping")
            total_mec = sum(site["mec_mw"] for site in sites)
            if total_mec <= 0:
                raise ValueError(f"forecast group {key} has no positive reviewed MEC")
            if forecast_mw > total_mec + 1e-8:
                raise ValueError(f"forecast group {key} exceeds reviewed MEC {total_mec:.3f} MW")
            for site in sites:
                by_bus[site["bus_id"]] += forecast_mw * site["mec_mw"] / total_mec
            totals[kind] += forecast_mw
    return dict(by_bus), totals


def balancing_dispatch(
    case: NetworkCase,
    *,
    required_mw: float,
    excluded_buses: set[int],
) -> dict[int, float]:
    required_mw = _finite(required_mw, "balancing generation", nonnegative=True)
    capacity: dict[int, dict[str, float]] = defaultdict(lambda: {"pmin": 0.0, "pmax": 0.0})
    for generator in case.generators:
        bus_id = int(generator["bus_id"])
        if not generator["in_service"] or bus_id in excluded_buses:
            continue
        pmin = max(0.0, _finite(generator.get("pmin_mw", 0.0), f"Pmin at bus {bus_id}"))
        pmax = max(pmin, _finite(generator.get("pmax_mw", generator.get("pg_mw", 0.0)), f"Pmax at bus {bus_id}"))
        capacity[bus_id]["pmin"] += pmin
        capacity[bus_id]["pmax"] += pmax
    if not capacity and required_mw > 1e-8:
        raise ValueError("no balancing generators remain after reviewed renewable allocation")
    total_min = sum(row["pmin"] for row in capacity.values())
    total_max = sum(row["pmax"] for row in capacity.values())
    if required_mw < total_min - 1e-8 or required_mw > total_max + 1e-8:
        raise ValueError(
            f"balancing dispatch {required_mw:.3f} MW is outside aggregate generator range "
            f"[{total_min:.3f}, {total_max:.3f}] MW"
        )
    dispatch = {bus: row["pmin"] for bus, row in capacity.items()}
    remaining = required_mw - total_min
    total_headroom = total_max - total_min
    if remaining > 1e-8 and total_headroom <= 0:
        raise ValueError("balancing generators have no dispatch headroom")
    if total_headroom > 0:
        for bus, row in capacity.items():
            dispatch[bus] += remaining * (row["pmax"] - row["pmin"]) / total_headroom
    return dispatch


def resolve_dc_transfer_overrides(
    case: NetworkCase,
    requested: Mapping[str, Any],
) -> dict[str, float]:
    if not requested:
        return {}
    available = {str(line["dc_line_id"]): line for line in case.dc_lines}
    resolved: dict[str, float] = {}
    for requested_id, value in requested.items():
        key = str(requested_id)
        if key in available:
            match = key
        else:
            folded = key.casefold()
            matches = [dc_id for dc_id in available if folded in dc_id.casefold()]
            if len(matches) != 1:
                raise ValueError(f"DC transfer {key!r} does not resolve uniquely to a parsed two-terminal DC line")
            match = matches[0]
        resolved[match] = _finite(value, f"DC transfer {key}")
    return resolved


def external_dc_import_mw(
    case: NetworkCase,
    overrides: Mapping[str, float],
) -> float:
    """Net scheduled DC import into the modeled AC grid from declared boundaries."""
    boundary = set(case.metadata.get("external_dc_boundary_bus_ids", []))
    active = {int(bus["bus_id"]) for bus in case.buses if bus["in_service"]}
    imported = 0.0
    for line in case.dc_lines:
        rectifier = int(line["rectifier_bus"])
        inverter = int(line["inverter_bus"])
        if not line.get("in_service", True) or {rectifier, inverter} - active:
            continue
        transfer = overrides.get(str(line["dc_line_id"]), line.get("scheduled_mw"))
        if transfer is None:
            continue
        if rectifier in boundary and inverter not in boundary:
            imported += float(transfer)
        elif inverter in boundary and rectifier not in boundary:
            imported -= float(transfer)
    return imported


def future_injection_adapter(
    case: NetworkCase,
    forecast: Mapping[str, Any],
    *,
    load_shares: Mapping[int, float],
    generation_groups: Mapping[tuple[str, str], list[dict[str, Any]]],
) -> tuple[dict[int, float], dict[str, float], dict[str, Any]]:
    demand_mw = _finite(forecast["demand_mw"], "demand_mw", nonnegative=True)
    renewable_by_bus, renewable_totals = allocate_regional_generation(
        forecast.get("regional_generation_mw", {}), generation_groups,
    )
    renewable_total = sum(renewable_totals.values())
    dc_overrides = resolve_dc_transfer_overrides(case, forecast.get("dc_transfers_mw", {}))
    external_import = external_dc_import_mw(case, dc_overrides)
    required_thermal = demand_mw - renewable_total - external_import
    if required_thermal < -1e-8:
        raise ValueError("renewable generation plus external DC import exceeds demand; curtailment or export assumption is required")
    thermal = balancing_dispatch(
        case,
        required_mw=max(0.0, required_thermal),
        excluded_buses=set(renewable_by_bus),
    )
    generation_by_bus: dict[int, float] = defaultdict(float)
    for bus, mw in renewable_by_bus.items():
        generation_by_bus[bus] += mw
    for bus, mw in thermal.items():
        generation_by_bus[bus] += mw
    load_by_bus = {int(bus): demand_mw * float(weight) for bus, weight in load_shares.items()}
    active_buses = {int(bus["bus_id"]) for bus in case.buses if bus["in_service"]}
    injections = {
        bus: generation_by_bus.get(bus, 0.0) - load_by_bus.get(bus, 0.0)
        for bus in active_buses
    }
    balance = sum(injections.values())
    if abs(balance + external_import) > 1e-6:
        raise AssertionError(
            f"future modeled AC injections plus DC import failed to balance by "
            f"{balance + external_import:.6f} MW"
        )
    return injections, dc_overrides, {
        "demand_mw": demand_mw,
        "renewable_generation_mw": renewable_totals,
        "balancing_generation_mw": sum(thermal.values()),
        "external_dc_import_mw": external_import,
        "net_ac_injection_before_dc_mw": balance,
        "modeled_ac_balance_after_dc_mw": balance + external_import,
    }


def _disable_kwargs(assets: Iterable[Asset]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    assets = tuple(assets)
    return (
        tuple(asset.asset_id for asset in assets if asset.asset_type == "branch"),
        tuple(asset.asset_id for asset in assets if asset.asset_type == "transformer"),
    )


def _solve(
    case: NetworkCase,
    injections: Mapping[int, float],
    dc_overrides: Mapping[str, float],
    disabled: Iterable[Asset],
) -> dict[str, Any]:
    branches, transformers = _disable_kwargs(disabled)
    return solve_dc_case(
        case,
        disabled_branches=branches,
        disabled_transformers=transformers,
        injection_overrides_mw=injections,
        dc_transfer_overrides_mw=dc_overrides,
    )


def _network_features(result: Mapping[str, Any]) -> dict[str, Any]:
    if result["status"] != "ok":
        return {
            "operable_state": False,
            "max_dc_loading_proxy_pct": None,
            "minimum_headroom_proxy_mw": None,
            "worst_asset": None,
            "n_assets_above_80pct": None,
        }
    rated = [flow for flow in result["flows"] if flow["loading_pct"] is not None]
    if not rated:
        return {
            "operable_state": True,
            "max_dc_loading_proxy_pct": None,
            "minimum_headroom_proxy_mw": None,
            "worst_asset": None,
            "n_assets_above_80pct": 0,
        }
    rated.sort(key=lambda flow: (-flow["loading_pct"], flow["asset_type"], flow["asset_id"]))
    headrooms = [flow["rating_mva"] - abs(flow["flow_mw"]) for flow in rated]
    return {
        "operable_state": True,
        "max_dc_loading_proxy_pct": float(rated[0]["loading_pct"]),
        "minimum_headroom_proxy_mw": float(min(headrooms)),
        "worst_asset": str(rated[0]["asset_id"]),
        "n_assets_above_80pct": sum(flow["loading_pct"] > 80.0 for flow in rated),
    }


def _asset_from_flow(flow: Mapping[str, Any]) -> Asset:
    if flow["asset_type"] == "transformer" and "/w" in str(flow["asset_id"]):
        return Asset("transformer", str(flow["asset_id"]).rsplit("/w", 1)[0])
    return Asset(str(flow["asset_type"]), str(flow["asset_id"]))


def screen_worst_contingency(
    case: NetworkCase,
    *,
    injections: Mapping[int, float],
    dc_overrides: Mapping[str, float],
    planned_outage: Asset,
    candidate_count: int = 10,
) -> tuple[Asset | None, list[dict[str, Any]]]:
    planned = _solve(case, injections, dc_overrides, (planned_outage,))
    if planned["status"] != "ok":
        return None, [{"status": planned["status"], "reason": planned.get("reason"), "asset": None}]
    rated = [flow for flow in planned["flows"] if flow["loading_pct"] is not None]
    rated.sort(key=lambda flow: (-flow["loading_pct"], flow["asset_type"], flow["asset_id"]))
    candidates: list[Asset] = []
    for flow in rated:
        asset = _asset_from_flow(flow)
        if asset == planned_outage or asset in candidates:
            continue
        candidates.append(asset)
        if len(candidates) >= candidate_count:
            break
    screening = []
    operable = []
    for asset in candidates:
        result = _solve(case, injections, dc_overrides, (planned_outage, asset))
        features = _network_features(result)
        row = {
            "asset": vars(asset),
            "status": result["status"],
            "security_event": result["status"] == "islanded",
            "max_dc_loading_proxy_pct": features["max_dc_loading_proxy_pct"],
            "worst_asset": features["worst_asset"],
        }
        screening.append(row)
        if result["status"] == "ok" and features["max_dc_loading_proxy_pct"] is not None:
            operable.append((features["max_dc_loading_proxy_pct"], asset.asset_type, asset.asset_id, asset))
    operable.sort(key=lambda item: (-item[0], item[1], item[2]))
    return (operable[0][3] if operable else None), screening


def _choose_network_scenario(
    planned: Mapping[str, Any],
    n_minus_one: Mapping[str, Any] | None,
) -> tuple[str, Mapping[str, Any], dict[str, Any]]:
    planned_features = _network_features(planned)
    if n_minus_one is None:
        return "planned-outage", planned, planned_features
    n1_features = _network_features(n_minus_one)
    if not n1_features["operable_state"]:
        return "planned-outage", planned, planned_features
    p = planned_features["max_dc_loading_proxy_pct"]
    n = n1_features["max_dc_loading_proxy_pct"]
    if n is not None and (p is None or n >= p):
        return "screened-n-1", n_minus_one, n1_features
    return "planned-outage", planned, planned_features


def build_network_forecast(
    case: NetworkCase,
    forecast_rows: list[dict[str, Any]],
    reviewed_crosswalk: list[dict[str, Any]],
    *,
    planned_outage: Asset = DEFAULT_PLANNED_OUTAGE,
    contingency_candidates: int = 10,
) -> list[dict[str, Any]]:
    if len(forecast_rows) != 48:
        raise ValueError("exactly 48 half-hour forecast rows are required")
    if contingency_candidates < 1:
        raise ValueError("contingency_candidates must be at least one")
    assets = (
        case.branches if planned_outage.asset_type == "branch"
        else case.transformers if planned_outage.asset_type == "transformer"
        else None
    )
    id_field = "asset_id" if planned_outage.asset_type == "branch" else "transformer_id"
    if assets is None or not any(
        asset[id_field] == planned_outage.asset_id and asset["in_service"]
        for asset in assets
    ):
        raise ValueError("planned outage must identify an in-service case asset")
    validate_forecast_rows(forecast_rows)
    load_shares = normalized_load_shares(case)
    generation_groups, mapping_confidence = reviewed_generation_groups(case, reviewed_crosswalk)

    snapshots = []
    for row in forecast_rows:
        injections, dc_overrides, adapter = future_injection_adapter(
            case,
            row,
            load_shares=load_shares,
            generation_groups=generation_groups,
        )
        intact = _solve(case, injections, dc_overrides, ())
        planned = _solve(case, injections, dc_overrides, (planned_outage,))
        snapshots.append({
            "row": row,
            "injections": injections,
            "dc_overrides": dc_overrides,
            "adapter": adapter,
            "intact": intact,
            "planned": planned,
            "planned_features": _network_features(planned),
        })

    operable_for_screen = [
        snap for snap in snapshots
        if snap["planned"]["status"] == "ok"
        and snap["planned_features"]["max_dc_loading_proxy_pct"] is not None
    ]
    if not operable_for_screen:
        raise ValueError("planned-outage topology is not operable for any forecast half-hour")
    peak = max(
        operable_for_screen,
        key=lambda snap: snap["planned_features"]["max_dc_loading_proxy_pct"],
    )
    worst_contingency, screening = screen_worst_contingency(
        case,
        injections=peak["injections"],
        dc_overrides=peak["dc_overrides"],
        planned_outage=planned_outage,
        candidate_count=contingency_candidates,
    )

    output = []
    islanding_candidates = sorted(
        item["asset"]["asset_id"]
        for item in screening
        if item["status"] == "islanded" and item["asset"] is not None
    )
    for snap in snapshots:
        row = snap["row"]
        n1 = (
            _solve(
                case,
                snap["injections"],
                snap["dc_overrides"],
                (planned_outage, worst_contingency),
            )
            if worst_contingency is not None else None
        )
        scenario_name, selected_solve, features = _choose_network_scenario(snap["planned"], n1)
        intact_features = _network_features(snap["intact"])
        n1_features = _network_features(n1) if n1 is not None else None

        def scenario_summary(result: Mapping[str, Any], summary: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "status": result["status"],
                "operable_state": summary["operable_state"],
                "worst_asset": summary["worst_asset"],
                "max_dc_loading_proxy_pct": summary["max_dc_loading_proxy_pct"],
                "minimum_headroom_proxy_mw": summary["minimum_headroom_proxy_mw"],
                "n_assets_above_80pct": summary["n_assets_above_80pct"],
            }

        drivers = list(row.get("drivers", []))
        outage_driver = str(row.get("planned_outage_driver", f"{planned_outage.asset_id} scheduled outage"))
        if outage_driver not in drivers:
            drivers.append(outage_driver)
        output.append({
            "valid_time": _format_time(_parse_time(str(row["valid_time"]))),
            "constraint_probability": float(row["constraint_probability"]),
            "expected_constraint_mwh": float(row["expected_constraint_mwh"]),
            "network": {
                "scenario": scenario_name,
                "worst_asset": features["worst_asset"],
                "max_dc_loading_proxy_pct": features["max_dc_loading_proxy_pct"],
                "minimum_headroom_proxy_mw": features["minimum_headroom_proxy_mw"],
                "worst_contingency": worst_contingency.asset_id if worst_contingency else None,
                "n_assets_above_80pct": features["n_assets_above_80pct"],
                "scenarios": {
                    "intact": scenario_summary(snap["intact"], intact_features),
                    "planned_outage": scenario_summary(snap["planned"], snap["planned_features"]),
                    "selected_n_minus_one": (
                        scenario_summary(n1, n1_features) if n1 is not None else None
                    ),
                },
                "screened_contingency_count": len(screening),
                "screened_islanding_contingencies": islanding_candidates,
                "security_event": bool(islanding_candidates or (n1 is not None and n1["status"] == "islanded")),
                "screening_scope": "top rated assets by planned-outage loading at the peak half-hour",
                "safety": evaluate_safety(
                    selected_solve, snsp_pct=row.get("snsp_pct"),
                ).to_dict(),
            },
            "drivers": drivers,
            "confidence": {
                "forecast": float(row["forecast_confidence"]),
                "forecast_issue_time": _format_time(_parse_time(str(row["issue_time"]))),
                "forecast_source": str(row["forecast_source"]),
                "network_asset_mapping": mapping_confidence,
                "network_state": "planning-scenario",
            },
        })
    return output


def build_network_forecast_from_files(
    *,
    case_dir: str | Path = DEFAULT_CASE_DIR,
    input_path: str | Path = DEFAULT_INPUT_PATH,
    crosswalk_path: str | Path = DEFAULT_CROSSWALK_PATH,
    planned_outage: Asset = DEFAULT_PLANNED_OUTAGE,
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    return build_network_forecast(
        load_case(case_dir),
        load_forecast_inputs(input_path, as_of=as_of),
        load_reviewed_crosswalk(crosswalk_path),
        planned_outage=planned_outage,
    )

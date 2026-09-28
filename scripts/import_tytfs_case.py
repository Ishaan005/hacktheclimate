"""Import and validate EirGrid's TYTFS 2024 summer PSS/E V33 case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.network import import_zip, solve_dc_case, write_case


def validation_report(case: object, result: dict) -> dict:
    buses = case.buses
    branches = case.branches
    transformers = case.transformers
    generators = case.generators
    loads = case.loads
    dc_lines = case.dc_lines
    active_generation = sum(g["pg_mw"] for g in generators if g["in_service"])
    active_load = sum(load["p_mw"] for load in loads if load["in_service"])
    rating_missing = lambda rows: sum(r["rate_a_mva"] <= 0 or r["rate_a_mva"] >= 9000 for r in rows)
    rated_flows = [f for f in result["flows"] if f["loading_pct"] is not None]
    internal_islands = [i for i in result["islands"] if not i.get("external_dc_boundary")]
    external_islands = [i for i in result["islands"] if i.get("external_dc_boundary")]
    star_x = []
    for t in transformers:
        if t["third_bus"]:
            x12, x23, x31 = t["x_pu"], t["x23_pu"], t["x31_pu"]
            star_x.extend(((x12+x31-x23)/2, (x12+x23-x31)/2, (x23+x31-x12)/2))
    return {
        "label": "TYTFS 2024 summer planning scenario; DC approximation, not live operations",
        "provenance": case.metadata,
        "source_records": {"buses": len(buses), "branches": len(branches), "transformers": len(transformers), "two_winding_transformers": sum(not t["third_bus"] for t in transformers), "three_winding_transformers": sum(bool(t["third_bus"]) for t in transformers), "generators": len(generators), "loads": len(loads), "two_terminal_dc_lines": len(dc_lines)},
        "in_service": {"buses": sum(b["in_service"] for b in buses), "branches": sum(b["in_service"] for b in branches), "transformers": sum(t["in_service"] for t in transformers), "generators": sum(g["in_service"] for g in generators), "loads": sum(load["in_service"] for load in loads), "two_terminal_dc_lines": sum(line["in_service"] for line in dc_lines)},
        "injection_mw": {
            "online_generation": active_generation,
            "online_constant_power_load": active_load,
            "source_ac_residual": active_generation - active_load,
            "applied_dc_transfers": result.get("dc_transfers_mw", {}),
            "modeled_ac_grid_residual_before_slack": sum(i["imbalance_mw"] for i in internal_islands),
            "external_boundary_residual": sum(i["imbalance_mw"] for i in external_islands),
            "combined_residual": result["balance_mw"],
        },
        "connectivity": {"components": len(result["islands"]), "islands": result["islands"]},
        "base_dc_solve": {"status": result["status"], "reason": result.get("reason"), "flow_count": len(result["flows"]), "max_abs_flow_mw": max((abs(f["flow_mw"]) for f in result["flows"]), default=None), "max_rated_loading_pct_proxy": max((f["loading_pct"] for f in rated_flows), default=None), "rated_flow_count": len(rated_flows), "rated_flows_over_100_pct_proxy": sum(f["loading_pct"] > 100 for f in rated_flows), "max_kcl_residual_mw": result["max_kcl_residual_mw"]},
        "rating_quality": {"branches_missing_or_placeholder_rate_a": rating_missing(branches), "transformer_parent_records_missing_or_placeholder_rate_a": rating_missing(transformers), "modeled_flow_records_without_rate_a": len(result["flows"]) - len(rated_flows), "rate_a_units": "MVA", "loading_proxy": "absolute DC MW / source RATEA MVA; not AC thermal loading"},
        "transformer_star_legs": {"nonpositive_raw_equivalent_x_count": sum(x <= 0 for x in star_x), "zero_x_approximated_count": sum(abs(x) <= 1e-8 for x in star_x)},
        "limitations": [
            "The source has solved AC bus voltage/angle fields but no authoritative solved branch MW flows for direct comparison.",
            "DC ignores resistance, losses, reactive power, voltage/security limits, shunts, and control actions.",
            "Two-terminal DC transfers are ideal equal/opposite MW injections; converter losses and controls are omitted. The isolated Scotland bus is an explicit external boundary.",
            "Only constant-power load terms are used; constant-current and constant-admittance terms are omitted.",
            "Three-winding transformers use a star equivalent with winding-specific taps, angles and ratings. Negative equivalent reactances are retained; zero legs are approximated by 1e-8 pu.",
            "0 and >=9000 MVA RATEA values are treated as missing/placeholder, not infinite certified limits.",
            "The raw file is an EirGrid planning scenario and does not represent 2026 topology or operations.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True, help="Downloaded TYTFS2024_studyfiles.zip")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/network_case"))
    args = parser.parse_args()
    case = import_zip(args.zip)
    result = solve_dc_case(case)
    if result["status"] == "unsolved":
        raise SystemExit(f"Base DC solve failed: {result['reason']}")
    write_case(case, args.output_dir)
    report = validation_report(case, result)
    (args.output_dir / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output_dir": str(args.output_dir), "status": result["status"], "source_records": report["source_records"], "connectivity": report["connectivity"], "injection_mw": report["injection_mw"]}, indent=2))


if __name__ == "__main__":
    main()

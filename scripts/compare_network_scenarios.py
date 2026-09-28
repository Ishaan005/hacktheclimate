"""Run a reviewed planned outage and selected N-1 in the TYTFS study case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.network import load_case
from backend.app.network_scenarios import Asset, compare_network_scenarios


def reviewed_outage(audit_path: Path, selected: Asset) -> dict:
    """Require the reviewed, in-service case match before opening it."""
    audit = json.loads(audit_path.read_text())
    item = audit["selected_outage"]
    annual, short_term = item["annual"], item["short_term"]
    match = item["network_match"]
    switch = match.get("scenario_switch", {})
    if annual["outage_id"] != short_term["outage_id"]:
        raise ValueError("outage audit publication IDs differ")
    if match["decision"] != "reviewed_scenario_candidate":
        raise ValueError("outage audit has no reviewed asset match")
    if (switch.get("asset_type"), switch.get("asset_id")) != (
        selected.asset_type,
        selected.asset_id,
    ) or switch.get("operation") != "set_in_service" or switch.get("value") is not False:
        raise ValueError("selected outage does not match the reviewed open switch")
    if match["candidate"].get("case_in_service") not in (True, "True"):
        raise ValueError("reviewed outage asset is not in service in the intact case")
    return {
        "sources": audit["sources"],
        "annual": annual,
        "short_term": short_term,
        "network_match": match,
    }


def _print_stress(report: dict) -> None:
    print("\nSystem-wide stress ranking")
    for name, stress in report["stress_ranking"]["runs"].items():
        print(f"{name}: actionable={stress['actionable']}")
        if not stress["actionable"]:
            continue
        breaches = stress["threshold_breaches"]
        print(
            "  threshold breaches: "
            f">80%={breaches['above_80pct']['count']}, "
            f">90%={breaches['above_90pct']['count']}, "
            f">100%={breaches['above_100pct']['count']}"
        )
        print("  top 10 loading proxies:")
        for row in stress["top_10_highest_loading_proxies"]:
            print(
                f"    {row['asset_type']} {row['asset_id']}: "
                f"{row['dc_loading_pct_proxy']:.2f}% "
                f"({row['flow_mw']:.2f} MW / {row['rating_mva']:.2f} MVA)"
            )
    for name, stress in report["stress_ranking"]["comparisons_from_intact"].items():
        if not stress["actionable"]:
            continue
        print(f"  {name} largest headroom decreases:")
        for row in stress["top_10_largest_headroom_decreases"]:
            print(f"    {row['asset_type']} {row['asset_id']}: {row['headroom_decrease_mw']:.2f} MW")
        print(f"  {name} largest absolute flow changes:")
        for row in stress["top_10_largest_absolute_flow_changes"]:
            print(f"    {row['asset_type']} {row['asset_id']}: {row['abs_delta_flow_mw']:.2f} MW")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--outage-type", choices=("branch", "transformer"), required=True)
    parser.add_argument("--outage-id", required=True)
    parser.add_argument("--outage-audit", required=True, type=Path)
    parser.add_argument("--contingency-type", choices=("branch", "transformer"), required=True)
    parser.add_argument("--contingency-id", required=True)
    parser.add_argument("--contingency-reference", required=True)
    parser.add_argument("--monitor-type", choices=("branch", "transformer"), required=True)
    parser.add_argument("--monitor-id", required=True)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    selected = Asset(args.outage_type, args.outage_id)
    review = reviewed_outage(args.outage_audit, selected)
    report = compare_network_scenarios(
        load_case(args.case_dir),
        planned_outage=selected,
        contingency=Asset(args.contingency_type, args.contingency_id),
        monitored=Asset(args.monitor_type, args.monitor_id),
        outage_reference=(
            f"{review['annual']['outage_id']}; annual programme row "
            f"{review['annual']['source_row']}; short-term row "
            f"{review['short_term']['source_row']}; scheduled/planned evidence only"
        ),
        contingency_reference=args.contingency_reference,
    )
    report["outage_review"] = review
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {args.output_json}")
    for name, run in report["runs"].items():
        monitor = report["monitor_by_run"][name]
        print(
            f"{name}: {run['status']}; monitored flow "
            f"{monitor['flow_mw'] if monitor else 'unavailable'} MW; "
            f"DC loading proxy {monitor['dc_loading_pct_proxy'] if monitor else 'unavailable'}%"
        )
    _print_stress(report)


if __name__ == "__main__":
    main()

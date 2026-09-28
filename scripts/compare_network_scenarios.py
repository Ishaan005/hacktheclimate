"""Run a reviewed planned outage and selected N-1 in the TYTFS study case.

Example (IDs must first be reviewed against the source publications)::

    python -m scripts.compare_network_scenarios \
      --case-dir data/raw/network_case \
      --outage-type branch --outage-id '1:2:1' \
      --outage-audit data/raw/network_case/outage_audit.json \
      --contingency-type branch --contingency-id '2:3:1' \
      --contingency-reference 'selected neighboring circuit in TYTFS study case' \
      --monitor-type branch --monitor-id '1:3:1' \
      --output-json data/raw/network_case/scenario.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.network import load_case
from backend.app.network_scenarios import Asset, compare_network_scenarios


def reviewed_outage(audit_path: Path, selected: Asset) -> dict:
    """Require #11's reviewed, in-service case match before opening it."""
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


if __name__ == "__main__":
    main()

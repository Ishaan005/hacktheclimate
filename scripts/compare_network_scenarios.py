"""Run a reviewed planned outage and selected N-1 in the TYTFS study case.

Example (IDs must first be reviewed against the source publications)::

    python -m scripts.compare_network_scenarios \
      --case-dir data/raw/network_case \
      --outage-type branch --outage-id '1:2:1' \
      --outage-reference '2026 outage programme, 7 Sep; reviewed asset ID ...' \
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--outage-type", choices=("branch", "transformer"), required=True)
    parser.add_argument("--outage-id", required=True)
    parser.add_argument("--outage-reference", required=True)
    parser.add_argument("--contingency-type", choices=("branch", "transformer"), required=True)
    parser.add_argument("--contingency-id", required=True)
    parser.add_argument("--contingency-reference", required=True)
    parser.add_argument("--monitor-type", choices=("branch", "transformer"), required=True)
    parser.add_argument("--monitor-id", required=True)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    report = compare_network_scenarios(
        load_case(args.case_dir),
        planned_outage=Asset(args.outage_type, args.outage_id),
        contingency=Asset(args.contingency_type, args.contingency_id),
        monitored=Asset(args.monitor_type, args.monitor_id),
        outage_reference=args.outage_reference,
        contingency_reference=args.contingency_reference,
    )
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

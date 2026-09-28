"""Publish one checked national constraint forecast from the latest daily GFS issue.

Run after 06:00 UTC, preferably near 06:15, from the repository root with
``python -m scripts.run_gfs_constraint_inference``. A failed run leaves the last
published result intact; the API rejects it when its forecast window expires.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from backend.app.gfs_forecast import DEFAULT_OUTPUT_DIR, run_issue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-date", help="UTC YYYY-MM-DD 00Z issue; defaults to the latest due issue")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    issue = datetime.fromisoformat(args.issue_date).replace(tzinfo=timezone.utc) if args.issue_date else None
    path = run_issue(issue=issue, output_dir=args.output_dir)
    print(f"Published checked experimental national forecast: {path}")


if __name__ == "__main__":
    main()

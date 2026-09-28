"""Create a 48 half-hour national constraint forecast from one GFS 00Z run."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

if __package__:
    from .train_gfs_constraint import build_forecast_rows, predict_one, validate_release_manifest
else:
    from train_gfs_constraint import build_forecast_rows, predict_one, validate_release_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weather", required=True, type=Path, help="One or more days from fetch_gfs_daily_panel.py")
    parser.add_argument("--model", type=Path, default=Path("artifacts/gfs_constraint/final_model.joblib"))
    parser.add_argument("--release-manifest", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug_release_manifest.json"),
                        help="All-lead NOAA release check for the supplied weather issue")
    parser.add_argument("--issue-date", help="YYYY-MM-DD; defaults to latest issue in the panel")
    parser.add_argument("--output", type=Path, default=Path(".cache/gfs_constraint_forecast.csv"))
    args = parser.parse_args()
    panel = pd.read_csv(args.weather)
    validate_release_manifest(panel, args.release_manifest)
    issue_date = args.issue_date or str(panel.issue_time_utc.max())[:10]
    panel = panel[panel.issue_time_utc.str.startswith(issue_date)].copy()
    if panel.empty:
        raise ValueError(f"No GFS 00Z issue for {issue_date}")
    rows, _ = build_forecast_rows(panel)
    if len(rows) != 48:
        raise ValueError(f"Expected 48 half-hour targets for one issue, got {len(rows)}")
    bundle = joblib.load(args.model)
    predictions = predict_one(bundle["model"], rows)
    output = rows[["issue_time_utc", "decision_time_utc", "target_time_utc", "horizon_hours", "source_snapshot_id", "source_available_at_utc"]].copy()
    for column in predictions:
        output[column] = predictions[column]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(f"Wrote {len(output)} forecast half-hours to {args.output}")


if __name__ == "__main__":
    main()

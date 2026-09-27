from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

if __package__:
    from .train_real_baseline import fit_hurdle, prepare_one_hour_frame
else:
    from train_real_baseline import fit_hurdle, prepare_one_hour_frame


def fold_masks(frame: pd.DataFrame, test_start: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    """Expanding training history and one calendar month of target-time holdout."""
    target_time = frame["target_1h_timestamp"]
    valid = frame["target_1h_mwh"].notna()
    test_end = test_start + pd.offsets.MonthBegin(1)
    train = valid & target_time.lt(test_start)
    test = valid & target_time.ge(test_start) & target_time.lt(test_end)
    return train, test


def backtest(input_path: Path, threshold_mwh: float = 5.0) -> dict:
    raw = pd.read_csv(input_path, parse_dates=["timestamp"])
    frame, features = prepare_one_hour_frame(raw)
    folds = []
    for month in range(4, 9):
        start = pd.Timestamp(year=2026, month=month, day=1)
        train, test = fold_masks(frame, start)
        if not train.any() or not test.any():
            raise ValueError(f"Insufficient labeled history for the {start:%Y-%m} fold")
        _, _, metrics = fit_hurdle(frame, features, "target_1h_mwh", train, test, threshold_mwh)
        folds.append({"test_month": f"{start:%Y-%m}", **metrics})

    return {
        "product": "1-hour operational forecast from measured system state at t",
        "caveat": "Retrospective expanding-window backtest; publication latency and weather forecast availability are not established. This is not a day-ahead forecast.",
        "input": str(input_path),
        "event_threshold_mwh": threshold_mwh,
        "feature_count": len(features),
        "folds": folds,
        "summary": {
            "median_pr_auc": float(np.median([f["occurrence_pr_auc"] for f in folds])),
            "min_pr_auc": float(min(f["occurrence_pr_auc"] for f in folds)),
            "max_pr_auc": float(max(f["occurrence_pr_auc"] for f in folds)),
            "mean_expected_volume_mae_mwh": float(np.mean([f["expected_volume_mae_mwh"] for f in folds])),
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Expanding-window monthly backtest of the 1-hour operational baseline.")
    p.add_argument("--input", type=Path, default=Path("data/processed/training_table_eirgrid_2026_jan_aug.csv"))
    p.add_argument("--output", type=Path, default=Path("artifacts/rolling_1h/metrics.json"))
    p.add_argument("--event-threshold-mwh", type=float, default=5.0)
    args = p.parse_args()

    result = backtest(args.input, args.event_threshold_mwh)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

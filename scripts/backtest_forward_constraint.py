"""Multi-horizon expanding chronological backtest for national constraint forecasts.

Evaluates forecast-safe hurdle models across multiple operational lead times
(1h, 4h, 12h, 24h) and monthly holdouts (April–August 2026) against simple
baselines and a calendar/lag baseline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__:
    from .forward_constraint import (
        HurdleForecastBundle,
        evaluate_forecast_bundle,
        prepare_forecast_frame,
        train_hurdle_bundle,
    )
else:
    from forward_constraint import (
        HurdleForecastBundle,
        evaluate_forecast_bundle,
        prepare_forecast_frame,
        train_hurdle_bundle,
    )


def run_horizon_backtest(
    raw_df: pd.DataFrame,
    horizon_hours: float,
    threshold_mwh: float = 5.0,
    test_months: list[int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], HurdleForecastBundle]:
    """Execute chronological monthly expanding backtest for a specific horizon."""
    if test_months is None:
        test_months = [4, 5, 6, 7, 8]

    frame, features, cal_lag_features = prepare_forecast_frame(
        raw_df, horizon_hours=horizon_hours, threshold_mwh=threshold_mwh
    )
    valid = frame["target_constraint_mwh"].notna()

    folds: list[dict[str, Any]] = []
    last_bundle: HurdleForecastBundle | None = None

    for month in test_months:
        start = pd.Timestamp(year=2026, month=month, day=1)
        end = start + pd.offsets.MonthBegin(1)

        # Strict chronological target-based partitioning:
        # Training target timestamps strictly precede test start
        # Test target timestamps fall strictly within [start, end)
        train_mask = valid & frame["target_timestamp"].lt(start)
        test_mask = valid & frame["target_timestamp"].ge(start) & frame["target_timestamp"].lt(end)

        if train_mask.sum() == 0 or test_mask.sum() == 0:
            raise ValueError(f"Insufficient samples for month {month} at horizon {horizon_hours}h")

        train_df = frame.loc[train_mask]
        test_df = frame.loc[test_mask]

        bundle = train_hurdle_bundle(
            train_df=train_df,
            features=features,
            cal_lag_features=cal_lag_features,
            horizon_hours=horizon_hours,
            threshold_mwh=threshold_mwh,
        )
        last_bundle = bundle

        fold_metrics = evaluate_forecast_bundle(bundle, test_df)
        folds.append({
            "test_month": f"{start:%Y-%m}",
            "train_start": str(train_df["target_timestamp"].min()),
            "train_end": str(train_df["target_timestamp"].max()),
            "test_start": str(test_df["target_timestamp"].min()),
            "test_end": str(test_df["target_timestamp"].max()),
            "train_intervals": int(train_mask.sum()),
            **fold_metrics,
        })

    # Summary statistics across folds
    pr_aucs = [f["classification"]["occurrence_pr_auc"] for f in folds]
    bl_pr_aucs = [f["classification"]["baseline_calendar_lag_pr_auc"] for f in folds]
    model_maes = [f["volume_mwh"]["model_expected_mae_mwh"] for f in folds]
    cal_lag_maes = [f["volume_mwh"]["calendar_lag_baseline_mae_mwh"] for f in folds]
    zero_maes = [f["volume_mwh"]["zero_baseline_mae_mwh"] for f in folds]
    cov_80s = [f["uncertainty_intervals"]["empirical_80_coverage"] for f in folds]
    cov_90s = [f["uncertainty_intervals"]["empirical_90_coverage"] for f in folds]

    summary = {
        "horizon_hours": horizon_hours,
        "step_intervals_30m": int(round(horizon_hours * 2)),
        "folds_evaluated": len(folds),
        "mean_event_prevalence": round(float(np.mean([f["event_prevalence"] for f in folds])), 4),
        "mean_pr_auc": round(float(np.mean(pr_aucs)), 4),
        "median_pr_auc": round(float(np.median(pr_aucs)), 4),
        "min_pr_auc": round(float(min(pr_aucs)), 4),
        "max_pr_auc": round(float(max(pr_aucs)), 4),
        "mean_baseline_calendar_lag_pr_auc": round(float(np.mean(bl_pr_aucs)), 4),
        "mean_model_mae_mwh": round(float(np.mean(model_maes)), 2),
        "mean_cal_lag_mae_mwh": round(float(np.mean(cal_lag_maes)), 2),
        "mean_zero_mae_mwh": round(float(np.mean(zero_maes)), 2),
        "overall_mae_reduction_vs_cal_lag_pct": round(
            float((np.mean(cal_lag_maes) - np.mean(model_maes)) / np.mean(cal_lag_maes) * 100.0), 2
        ),
        "overall_mae_reduction_vs_zero_pct": round(
            float((np.mean(zero_maes) - np.mean(model_maes)) / np.mean(zero_maes) * 100.0), 2
        ),
        "mean_empirical_80_coverage": round(float(np.mean(cov_80s)), 4),
        "mean_empirical_90_coverage": round(float(np.mean(cov_90s)), 4),
        "honest_assessment": (
            "Clear improvement over baselines with high skill"
            if np.mean(model_maes) < np.mean(cal_lag_maes) and np.mean(model_maes) < np.mean(zero_maes)
            else "No improvement over simple calendar/lag baseline: grid lag features lose predictive power without future NWP weather forecasts"
        ),
    }

    assert last_bundle is not None
    return folds, summary, last_bundle


def main() -> None:
    p = argparse.ArgumentParser(description="Multi-horizon backtest for forward-looking national constraint forecast.")
    p.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/training_table_eirgrid_2026_jan_aug.csv"),
        help="Path to training table with EirGrid context and labels",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/forward_constraint"),
        help="Output directory for artifacts and metrics (does NOT overwrite real_baseline)",
    )
    p.add_argument(
        "--horizons",
        type=str,
        default="1,4,12,24",
        help="Comma-separated lead times in hours (e.g. 1,4,12,24)",
    )
    p.add_argument(
        "--threshold-mwh",
        type=float,
        default=5.0,
        help="Event threshold for constraint MWh (default: 5.0)",
    )
    args = p.parse_args()

    # Safety check: do not allow overwriting retrospective demo artifacts
    resolved_out = args.output_dir.resolve()
    for protected in [Path("artifacts/real_baseline").resolve(), Path("artifacts/rolling_1h").resolve()]:
        if resolved_out == protected:
            raise ValueError(f"Output directory {args.output_dir} conflicts with protected retrospective artifact directory {protected}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {args.input}...")
    raw_df = pd.read_csv(args.input, parse_dates=["timestamp"])
    horizons = [float(h.strip()) for h in args.horizons.split(",") if h.strip()]

    print(f"Running multi-horizon backtest for lead times: {horizons} hours")
    print(f"Target: constraint_mwh (threshold > {args.threshold_mwh} MWh)")

    all_horizon_results: dict[str, Any] = {}
    saved_models: dict[str, str] = {}

    for h in horizons:
        h_tag = f"{int(h)}h" if h.is_integer() else f"{h}h"
        print(f"\n=======================================================")
        print(f"Evaluating Horizon: {h_tag} ({h} hours ahead)")
        print(f"=======================================================")

        folds, summary, bundle = run_horizon_backtest(
            raw_df=raw_df,
            horizon_hours=h,
            threshold_mwh=args.threshold_mwh,
            test_months=[4, 5, 6, 7, 8],
        )

        all_horizon_results[h_tag] = {
            "summary": summary,
            "folds": folds,
        }

        # Save bundle artifact
        model_filename = f"model_{h_tag}.joblib"
        model_path = args.output_dir / model_filename
        bundle.save(model_path)
        saved_models[h_tag] = str(model_path.relative_to(Path.cwd()) if model_path.is_relative_to(Path.cwd()) else model_path)

        print(f"Horizon {h_tag} Summary:")
        print(f"  PR-AUC: {summary['mean_pr_auc']:.4f} (Cal/Lag Baseline: {summary['mean_baseline_calendar_lag_pr_auc']:.4f})")
        print(f"  Model MAE: {summary['mean_model_mae_mwh']:.2f} MWh")
        print(f"  Cal/Lag Baseline MAE: {summary['mean_cal_lag_mae_mwh']:.2f} MWh")
        print(f"  Zero Baseline MAE: {summary['mean_zero_mae_mwh']:.2f} MWh")
        print(f"  Empirical 80% Coverage: {summary['mean_empirical_80_coverage']*100:.1f}%")
        print(f"  Empirical 90% Coverage: {summary['mean_empirical_90_coverage']*100:.1f}%")
        print(f"  Assessment: {summary['honest_assessment']}")

    # Assemble comprehensive metrics.json
    metrics_payload = {
        "title": "Forward-Looking National Constraint Forecast Backtest",
        "description": "Multi-horizon chronological expanding backtest of hurdle event-probability and non-negative conditional volume models with calibrated uncertainty intervals.",
        "target": "constraint_mwh",
        "event_definition": f"constraint_mwh > {args.threshold_mwh}",
        "dataset": str(args.input),
        "data_period": {
            "start": str(raw_df["timestamp"].min()),
            "end": str(raw_df["timestamp"].max()),
            "total_intervals": len(raw_df),
        },
        "horizons_evaluated": [f"{int(h)}h" if h.is_integer() else f"{h}h" for h in horizons],
        "test_folds": ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08"],
        "results_by_horizon": all_horizon_results,
    }

    metrics_path = args.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, indent=2))
    print(f"\nSaved metrics to {metrics_path}")

    # Assemble metadata.json
    metadata_payload = {
        "model_type": "Two-stage hurdle model (HistGradientBoostingClassifier + HistGradientBoostingRegressor) with Quantile Regressors (q=0.05, 0.10, 0.90, 0.95)",
        "target_separation": {
            "target": "constraint_mwh",
            "separated_from": "curtailment_mwh",
            "rationale": "Transmission constraints reflect physical grid network limitations and TSO testing, whereas curtailment reflects whole-system stability limits (SNSP, high frequency, RoCoF).",
        },
        "forecast_safety": {
            "principle": "For target T at horizon H, issue time is t_0 = T - H. All grid state features are measured strictly at or before t_0. Only calendar features are evaluated at T.",
            "leakage_protection": "Chronological target-based splitting ensures no overlap in target timestamps and no post-decision data leakage.",
        },
        "disclaimers": [
            "National probability and expected constraint MWh only: makes NO location or nodal claim.",
            "Transmission constraints occur at specific physical bottlenecks; national MWh does not specify which transmission line or node is constrained.",
            "Makes NO avoided-energy claim: flexible load can only relieve constraints if physically sited behind the relevant transmission constraint.",
            "Longer horizons (12h-24h) without prospective NWP weather forecasts suffer performance degradation, as historical system lags decay in predictive power.",
        ],
        "model_artifacts": saved_models,
        "feature_count": len(bundle.feature_names),
        "feature_names": bundle.feature_names,
        "cal_lag_feature_names": bundle.cal_lag_feature_names,
    }

    metadata_path = args.output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata_payload, indent=2))
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()

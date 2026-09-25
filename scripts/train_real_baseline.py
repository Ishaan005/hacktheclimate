from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import average_precision_score, mean_absolute_error, precision_score, recall_score, roc_auc_score

BASE_FEATURES = [
    "sem_price_currency_per_mwh",
    "eirgrid_ie_demand_mw",
    "eirgrid_ie_wind_availability_mw",
    "eirgrid_ie_wind_generation_mw",
    "eirgrid_ie_solar_availability_mw",
    "eirgrid_ie_solar_generation_mw",
    "eirgrid_ewic_ic_mw",
    "eirgrid_greenlink_ic_mw",
    "eirgrid_interjurisdictional_flow_mw",
    "eirgrid_snsp_pct",
    "eirgrid_ai_oversupply_mw",
]


def calendar_features(df: pd.DataFrame, timestamp: pd.Series, prefix: str = "") -> list[str]:
    hour = timestamp.dt.hour + timestamp.dt.minute / 60.0
    dow = timestamp.dt.dayofweek
    cols = []
    for name, values in {
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "dow_sin": np.sin(2 * np.pi * dow / 7),
        "dow_cos": np.cos(2 * np.pi * dow / 7),
    }.items():
        col = prefix + name
        df[col] = values
        cols.append(col)
    return cols


def fit_hurdle(df: pd.DataFrame, features: list[str], target: str, train_mask: pd.Series, test_mask: pd.Series, threshold: float):
    X = df[features]
    y = df[target]
    event = (y > threshold).astype(int)

    clf = HistGradientBoostingClassifier(max_depth=5, learning_rate=0.05, max_iter=150, random_state=42)
    clf.fit(X.loc[train_mask], event.loc[train_mask])

    positive_train = train_mask & (y > threshold)
    reg = HistGradientBoostingRegressor(max_depth=5, learning_rate=0.05, max_iter=150, random_state=42)
    reg.fit(X.loc[positive_train], y.loc[positive_train])

    p = clf.predict_proba(X.loc[test_mask])[:, 1]
    positive_volume = np.maximum(reg.predict(X.loc[test_mask]), 0)
    expected = p * positive_volume
    y_test = y.loc[test_mask].to_numpy()
    e_test = event.loc[test_mask].to_numpy()
    pred = (p >= 0.5).astype(int)

    return clf, reg, {
        "train_rows": int(train_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "test_event_rate": float(e_test.mean()),
        "occurrence_pr_auc": float(average_precision_score(e_test, p)),
        "occurrence_roc_auc": float(roc_auc_score(e_test, p)),
        "precision_at_0_5": float(precision_score(e_test, pred, zero_division=0)),
        "recall_at_0_5": float(recall_score(e_test, pred, zero_division=0)),
        "expected_volume_mae_mwh": float(mean_absolute_error(y_test, expected)),
        "zero_baseline_mae_mwh": float(mean_absolute_error(y_test, np.zeros_like(y_test))),
        "train_mean_baseline_mae_mwh": float(mean_absolute_error(y_test, np.full_like(y_test, y.loc[train_mask].mean(), dtype=float))),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/processed/training_table_labeled_jan2026.csv"))
    p.add_argument("--output-dir", type=Path, default=Path("artifacts/real_baseline"))
    p.add_argument("--split", default="2026-01-24")
    p.add_argument("--event-threshold-mwh", type=float, default=5.0)
    args = p.parse_args()

    df = pd.read_csv(args.input, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    features = [c for c in BASE_FEATURES if c in df.columns]
    features += calendar_features(df, df["timestamp"])
    split = pd.Timestamp(args.split)
    train = df["timestamp"] < split
    test = ~train

    now_clf, now_reg, now_metrics = fit_hurdle(
        df, features, "dispatch_down_total_mwh", train, test, args.event_threshold_mwh
    )

    # True operational 1-hour-ahead setup: measurements at t predict DD at t+1h.
    ahead = df.copy()
    ahead["target_1h_mwh"] = ahead["dispatch_down_total_mwh"].shift(-2)
    forecast_features = list(features)
    for col in [
        "eirgrid_ie_demand_mw", "eirgrid_ie_wind_availability_mw", "eirgrid_ie_wind_generation_mw",
        "eirgrid_snsp_pct", "sem_price_currency_per_mwh", "eirgrid_ewic_ic_mw", "eirgrid_greenlink_ic_mw"
    ]:
        if col in ahead:
            name = f"{col}_delta_1h"
            ahead[name] = ahead[col] - ahead[col].shift(2)
            forecast_features.append(name)
    forecast_features += calendar_features(ahead, ahead["timestamp"] + pd.Timedelta(hours=1), prefix="target_")
    valid = ahead["target_1h_mwh"].notna()
    train_1h = (ahead["timestamp"] < split) & valid
    test_1h = (ahead["timestamp"] >= split) & valid
    fc_clf, fc_reg, fc_metrics = fit_hurdle(
        ahead, forecast_features, "target_1h_mwh", train_1h, test_1h, args.event_threshold_mwh
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": now_clf, "features": features, "threshold_mwh": args.event_threshold_mwh}, args.output_dir / "nowcast_occurrence.joblib")
    joblib.dump({"model": now_reg, "features": features, "threshold_mwh": args.event_threshold_mwh}, args.output_dir / "nowcast_volume.joblib")
    joblib.dump({"model": fc_clf, "features": forecast_features, "threshold_mwh": args.event_threshold_mwh}, args.output_dir / "forecast_1h_occurrence.joblib")
    joblib.dump({"model": fc_reg, "features": forecast_features, "threshold_mwh": args.event_threshold_mwh}, args.output_dir / "forecast_1h_volume.joblib")

    metrics = {
        "warning": "Hackathon baseline on one month only. Use rolling multi-month backtests before making performance claims.",
        "event_definition": f"dispatch_down_total_mwh > {args.event_threshold_mwh}",
        "chronological_split": args.split,
        "nowcast_same_period": now_metrics,
        "forecast_1h_ahead": fc_metrics,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

"""Train a forecast-safe national constraint model on archived GFS vintages.

One NOAA GFS 00Z cycle is used for each 06Z decision. Its 100 m weather
forecasts are held constant within each forecast hour to align to the official
half-hour constraint labels. The model has no same-period EirGrid measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error


EVENT_THRESHOLD_MWH = 5.0
CALENDAR_FEATURES = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos", "horizon_hours"]
TARGETS = ("constraint_mwh", "curtailment_mwh")


def event_column(target: str) -> str:
    if target not in TARGETS:
        raise ValueError(f"Unsupported target: {target}")
    return target.removesuffix("_mwh") + "_event"


def _utc_naive(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.tz_convert(None)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_release_manifest(panel: pd.DataFrame, path: Path) -> None:
    if not path.exists():
        raise ValueError(f"Run verify_gfs_source_availability.py before training: {path} is missing")
    manifest = json.loads(path.read_text())
    days = manifest["days"]
    by_issue = {day["issue_time_utc"]: day for day in days}
    if len(by_issue) != len(days) or set(by_issue) != set(panel.issue_time_utc.unique()):
        raise ValueError("Release manifest does not cover every GFS issue")
    for issue, group in panel.groupby("issue_time_utc"):
        day = by_issue[issue]
        if sorted(item["lead_hours"] for item in day["lead_objects"]) != list(range(6, 31)):
            raise ValueError(f"Release manifest lacks forecast hours 6-30 for {issue}")
        latest = max(item["last_modified_utc"] for item in day["lead_objects"])
        if latest != day["source_available_at_utc"] or set(group.source_available_at_utc) != {latest}:
            raise ValueError(f"Panel availability differs from checked source objects for {issue}")


def build_forecast_rows(panel: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Create future half-hour features and reject late or malformed source data."""
    weather = panel.copy()
    for column in ("issue_time_utc", "decision_time_utc", "valid_time_utc", "source_available_at_utc"):
        weather[column] = _utc_naive(weather[column])
    if weather.duplicated(["issue_time_utc", "valid_time_utc"]).any():
        raise ValueError("Duplicate weather issue/valid pair")
    if (weather.valid_time_utc != weather.issue_time_utc + pd.to_timedelta(weather.lead_hours, unit="h")).any():
        raise ValueError("Weather valid time does not equal issue plus lead")
    if (weather.decision_time_utc != weather.issue_time_utc + pd.Timedelta(hours=6)).any():
        raise ValueError("Decision is not six hours after the GFS cycle")
    if (weather.source_available_at_utc > weather.decision_time_utc).any():
        raise ValueError("Weather source became available after decision")
    weather_features = [column for column in weather if column.endswith(("_wind_speed_100m", "_wind_u_100m", "_wind_v_100m", "_temperature_2m", "_downward_short_wave_radiation_flux_surface")) or column in ("mean_wind_speed_100m", "west_wind_speed_100m", "south_wind_speed_100m", "mean_temperature_2m_c", "mean_solar_w_m2")]
    if not weather_features:
        raise ValueError("No GFS weather features")
    if weather[weather_features].isna().any().any():
        raise ValueError("Missing weather feature")

    issue_rows = weather[["issue_time_utc", "decision_time_utc", "source_available_at_utc"]].drop_duplicates()
    if issue_rows.duplicated("issue_time_utc").any():
        raise ValueError("Inconsistent per-issue metadata")
    issue_rows = issue_rows.loc[issue_rows.index.repeat(48)].reset_index(drop=True)
    issue_rows["horizon_hours"] = np.tile(np.arange(1, 49) / 2.0, len(issue_rows) // 48)
    issue_rows["target_time_utc"] = issue_rows.decision_time_utc + pd.to_timedelta(issue_rows.horizon_hours, unit="h")
    issue_rows["weather_valid_time_utc"] = issue_rows.target_time_utc.dt.floor("h")
    table = issue_rows.merge(
        weather.drop(columns=["decision_time_utc", "source_available_at_utc"]),
        left_on=["issue_time_utc", "weather_valid_time_utc"],
        right_on=["issue_time_utc", "valid_time_utc"],
        how="left", validate="many_to_one",
    )
    if table[weather_features].isna().any().any():
        raise ValueError("Missing forecast hour for half-hour target")
    if table.target_time_utc.duplicated().any():
        raise ValueError("Target appears at multiple decisions")
    if not ((table.issue_time_utc < table.decision_time_utc) &
            (table.source_available_at_utc <= table.decision_time_utc) &
            (table.decision_time_utc < table.target_time_utc) &
            (table.valid_time_utc <= table.target_time_utc)).all():
        raise ValueError("Post-decision weather or non-future target")
    hour = table.target_time_utc.dt.hour + table.target_time_utc.dt.minute / 60
    dow = table.target_time_utc.dt.dayofweek
    month = table.target_time_utc.dt.month
    table["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    table["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    table["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    table["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    table["month_sin"] = np.sin(2 * np.pi * month / 12)
    table["month_cos"] = np.cos(2 * np.pi * month / 12)
    return table.sort_values("target_time_utc").reset_index(drop=True), CALENDAR_FEATURES + weather_features


def build_training_table(panel: pd.DataFrame, labels: pd.DataFrame, *, target: str = "constraint_mwh") -> tuple[pd.DataFrame, list[str]]:
    """Join only target labels to already checked forecast-safe features."""
    table, features = build_forecast_rows(panel)
    measured = labels[["timestamp", "constraint_mwh", "curtailment_mwh"]].copy()
    measured["timestamp"] = _utc_naive(measured.timestamp)
    if measured.duplicated("timestamp").any():
        raise ValueError("Duplicate label timestamp")
    table = table.merge(measured, left_on="target_time_utc", right_on="timestamp", how="inner", validate="one_to_one")
    if not np.isfinite(table[list(TARGETS)].to_numpy()).all() or (table[list(TARGETS)] < 0).any().any():
        raise ValueError("Missing, non-finite or negative dispatch-down label")
    table[event_column(target)] = (table[target] > EVENT_THRESHOLD_MWH).astype(int)
    return table, features


def _conformal_quantile(residuals: np.ndarray, coverage: float) -> float:
    n = len(residuals)
    rank = min(n, int(np.ceil((n + 1) * coverage)))
    return float(np.sort(residuals)[rank - 1])


def _fit_one(train: pd.DataFrame, calibration: pd.DataFrame, features: list[str], target: str) -> dict:
    event = event_column(target)
    y_event = train[event].to_numpy()
    if len(set(y_event)) < 2 or (y_event == 1).sum() < 30:
        raise ValueError("Not enough positive and negative training examples")
    classifier = HistGradientBoostingClassifier(max_iter=150, max_depth=4, learning_rate=0.05,
                                                l2_regularization=5.0, random_state=42)
    classifier.fit(train[features], y_event)
    volume = HistGradientBoostingRegressor(max_iter=150, max_depth=4, learning_rate=0.05,
                                           l2_regularization=5.0, random_state=42)
    volume.fit(train.loc[train[event].eq(1), features],
               train.loc[train[event].eq(1), target])
    raw_cal = classifier.predict_proba(calibration[features])[:, 1]
    calibrator = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
    calibrator.fit(raw_cal, calibration[event].to_numpy())
    cal_probability = calibrator.transform(raw_cal)
    cal_conditional = np.maximum(volume.predict(calibration[features]), 0)
    cal_expected = cal_probability * cal_conditional
    residuals = np.abs(calibration[target].to_numpy() - cal_expected)
    return {
        "features": features,
        "classifier": classifier,
        "conditional_volume": volume,
        "probability_calibrator": calibrator,
        "interval_radius_80_mwh": _conformal_quantile(residuals, 0.80),
        "interval_radius_90_mwh": _conformal_quantile(residuals, 0.90),
        "train_target_start": str(train.target_time_utc.min()),
        "train_target_end": str(train.target_time_utc.max()),
        "calibration_target_start": str(calibration.target_time_utc.min()),
        "calibration_target_end": str(calibration.target_time_utc.max()),
    }


def fit_bundle(train: pd.DataFrame, calibration: pd.DataFrame, weather_features: list[str], *, target: str = "constraint_mwh") -> dict:
    if train.target_time_utc.max() >= calibration.target_time_utc.min():
        raise ValueError("Training and calibration target periods overlap")
    return {
        "model": _fit_one(train, calibration, weather_features, target),
        "calendar_baseline": _fit_one(train, calibration, CALENDAR_FEATURES, target),
        "target": target,
        "event_threshold_mwh": EVENT_THRESHOLD_MWH,
        "forecast_source": "NOAA GFS via dynamical.org, 00Z issue for 06Z daily decision",
    }


def predict_one(model: dict, rows: pd.DataFrame) -> pd.DataFrame:
    features = model["features"]
    probability = np.clip(model["probability_calibrator"].transform(
        model["classifier"].predict_proba(rows[features])[:, 1]), 0, 1)
    conditional = np.maximum(model["conditional_volume"].predict(rows[features]), 0)
    expected = probability * conditional
    result = pd.DataFrame({"probability": probability, "expected_mwh": expected}, index=rows.index)
    for coverage in (80, 90):
        radius = model[f"interval_radius_{coverage}_mwh"]
        result[f"lower_{coverage}_mwh"] = np.maximum(0, expected - radius)
        result[f"upper_{coverage}_mwh"] = expected + radius
    return result


def _ece(y: np.ndarray, probability: np.ndarray) -> float:
    bins = np.minimum((probability * 10).astype(int), 9)
    return float(sum(abs(probability[bins == b].mean() - y[bins == b].mean()) * (bins == b).mean()
                     for b in range(10) if (bins == b).any()))


def metrics(rows: pd.DataFrame, forecast: pd.DataFrame, baseline: pd.DataFrame, *, target: str = "constraint_mwh") -> dict:
    y = rows[target].to_numpy()
    event = rows[event_column(target)].to_numpy()
    p = forecast.probability.to_numpy()
    return {
        "rows": len(rows),
        "event_prevalence": float(event.mean()),
        "event_pr_auc": float(average_precision_score(event, p)) if len(set(event)) > 1 else None,
        "calendar_event_pr_auc": float(average_precision_score(event, baseline.probability)) if len(set(event)) > 1 else None,
        "event_brier": float(brier_score_loss(event, p)),
        "calendar_event_brier": float(brier_score_loss(event, baseline.probability)),
        "event_ece_10_bins": _ece(event, p),
        "expected_mae_mwh": float(mean_absolute_error(y, forecast.expected_mwh)),
        "calendar_expected_mae_mwh": float(mean_absolute_error(y, baseline.expected_mwh)),
        "zero_mae_mwh": float(mean_absolute_error(y, np.zeros_like(y))),
        "interval_80_coverage": float(((y >= forecast.lower_80_mwh) & (y <= forecast.upper_80_mwh)).mean()),
        "interval_90_coverage": float(((y >= forecast.lower_90_mwh) & (y <= forecast.upper_90_mwh)).mean()),
        "interval_80_mean_width_mwh": float((forecast.upper_80_mwh - forecast.lower_80_mwh).mean()),
        "interval_90_mean_width_mwh": float((forecast.upper_90_mwh - forecast.lower_90_mwh).mean()),
    }


def evaluate_fold(train: pd.DataFrame, calibration: pd.DataFrame, test: pd.DataFrame,
                  features: list[str], *, target: str = "constraint_mwh") -> tuple[dict, dict, pd.DataFrame]:
    if train.target_time_utc.max() >= calibration.target_time_utc.min() or calibration.target_time_utc.max() >= test.target_time_utc.min():
        raise ValueError("Chronological fold periods overlap")
    bundle = fit_bundle(train, calibration, features, target=target)
    forecast = predict_one(bundle["model"], test)
    baseline = predict_one(bundle["calendar_baseline"], test)
    result = {
        "train_start": str(train.target_time_utc.min()),
        "train_end": str(train.target_time_utc.max()),
        "calibration_start": str(calibration.target_time_utc.min()),
        "calibration_end": str(calibration.target_time_utc.max()),
        "test_start": str(test.target_time_utc.min()),
        "test_end": str(test.target_time_utc.max()),
        "all_horizons": metrics(test, forecast, baseline, target=target),
        "exact_horizons": {},
        "horizon_bands": {},
    }
    for horizon in (1.0, 6.0, 12.0, 24.0):
        mask = test.horizon_hours.eq(horizon)
        result["exact_horizons"][f"{int(horizon)}h"] = metrics(test[mask], forecast[mask], baseline[mask], target=target)
    for name, low, high in (("0.5-6h", 0.5, 6), ("6.5-12h", 6.5, 12), ("12.5-24h", 12.5, 24)):
        mask = test.horizon_hours.between(low, high)
        result["horizon_bands"][name] = metrics(test[mask], forecast[mask], baseline[mask], target=target)
    predictions = test[["issue_time_utc", "decision_time_utc", "target_time_utc", "horizon_hours", "source_snapshot_id", "constraint_mwh", "curtailment_mwh", event_column(target)]].copy()
    for prefix, frame in (("model", forecast), ("calendar", baseline)):
        for column in frame:
            predictions[f"{prefix}_{column}"] = frame[column]
    return result, bundle, predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, default="constraint_mwh")
    parser.add_argument("--weather", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug.csv"))
    parser.add_argument("--labels", type=Path, default=Path("data/processed/training_table_eirgrid_2026_jan_aug.csv"))
    parser.add_argument("--release-manifest", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug_release_manifest.json"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--table", type=Path)
    args = parser.parse_args()
    target_name = args.target.removesuffix("_mwh")
    args.output_dir = args.output_dir or Path(f"artifacts/gfs_{target_name}")
    args.table = args.table or Path(f"data/processed/gfs_{target_name}_training_2026_jan_aug.csv")
    panel = pd.read_csv(args.weather)
    validate_release_manifest(panel, args.release_manifest)
    labels = pd.read_csv(args.labels)
    table, features = build_training_table(panel, labels, target=args.target)
    args.table.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.table, index=False)
    source_versions = {
        "weather_csv_sha256": _sha256(args.weather),
        "labels_csv_sha256": _sha256(args.labels),
        "training_table_csv_sha256": _sha256(args.table),
        "training_script_sha256": _sha256(Path(__file__)),
        "scikit_learn": sklearn.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "source_snapshot_ids": sorted(table.source_snapshot_id.unique().tolist()),
        "release_manifest_sha256": _sha256(args.release_manifest),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    folds = {}
    all_predictions = []
    august_bundle = None
    august_predictions = None
    for month in (4, 5, 6, 7, 8):
        test_start = pd.Timestamp(f"2026-{month:02d}-01")
        calibration_start = test_start - pd.DateOffset(months=1)
        test_end = test_start + pd.DateOffset(months=1)
        train = table[table.target_time_utc < calibration_start]
        calibration = table[table.target_time_utc.between(calibration_start, test_start, inclusive="left")]
        test = table[table.target_time_utc.between(test_start, test_end, inclusive="left")]
        if min(len(train), len(calibration), len(test)) == 0:
            raise ValueError(f"Empty train/calibration/test fold for {test_start}")
        result, bundle, predictions = evaluate_fold(train, calibration, test, features, target=args.target)
        folds[f"2026-{month:02d}"] = result
        predictions["test_month"] = f"2026-{month:02d}"
        all_predictions.append(predictions)
        print(f"{test_start:%Y-%m}: {result['all_horizons']['expected_mae_mwh']:.2f} MWh MAE vs calendar {result['all_horizons']['calendar_expected_mae_mwh']:.2f}", flush=True)
        if month == 8:
            august_bundle, august_predictions = bundle, predictions
    assert august_bundle is not None and august_predictions is not None
    august_bundle["source_versions"] = source_versions
    joblib.dump(august_bundle, args.output_dir / "heldout_august_model.joblib")
    august_predictions.to_csv(args.output_dir / "august_holdout_predictions.csv", index=False)
    backtest_predictions = pd.concat(all_predictions, ignore_index=True)
    backtest_predictions.to_csv(args.output_dir / "backtest_predictions.csv", index=False)
    model_predictions = backtest_predictions[[column for column in backtest_predictions if column.startswith("model_")]].rename(columns=lambda column: column.removeprefix("model_"))
    calendar_predictions = backtest_predictions[[column for column in backtest_predictions if column.startswith("calendar_")]].rename(columns=lambda column: column.removeprefix("calendar_"))
    aggregate = {"all_horizons": metrics(backtest_predictions, model_predictions, calendar_predictions, target=args.target), "exact_horizons": {}, "horizon_bands": {}}
    for horizon in (1.0, 6.0, 12.0, 24.0):
        mask = backtest_predictions.horizon_hours.eq(horizon)
        aggregate["exact_horizons"][f"{int(horizon)}h"] = metrics(backtest_predictions[mask], model_predictions[mask], calendar_predictions[mask], target=args.target)
    for name, low, high in (("0.5-6h", 0.5, 6), ("6.5-12h", 6.5, 12), ("12.5-24h", 12.5, 24)):
        mask = backtest_predictions.horizon_hours.between(low, high)
        aggregate["horizon_bands"][name] = metrics(backtest_predictions[mask], model_predictions[mask], calendar_predictions[mask], target=args.target)
    final_train = table[table.target_time_utc < pd.Timestamp("2026-08-01")]
    final_calibration = table[table.target_time_utc >= pd.Timestamp("2026-08-01")]
    final_bundle = fit_bundle(final_train, final_calibration, features, target=args.target)
    final_bundle["source_versions"] = source_versions
    joblib.dump(final_bundle, args.output_dir / "final_model.joblib")
    monthly = {}
    for month, group in table.groupby(table.target_time_utc.dt.to_period("M")):
        monthly[str(month)] = {"rows": len(group), "event_prevalence": float(group[event_column(args.target)].mean()),
                               "missing_feature_values": int(group[features].isna().sum().sum())}
    report = {
        "target": f"national {args.target}; other dispatch-down component retained only as a separate label",
        "event_definition": f"{args.target} > {EVENT_THRESHOLD_MWH} MWh per half-hour",
        "issue_and_decision": "Daily NOAA GFS 00Z run, all used forecast-hour objects present by 06Z decision",
        "weather_mapping": "Forecast hour at or before each target half-hour; no invented 30-minute meteorology",
        "feature_availability": "NOAA object Last-Modified <= decision; no EirGrid actuals or label lags as predictors",
        "publication_caveat": "NOAA S3 Last-Modified is a source-availability proxy, not a provider SLA or live ingest log",
        "train_table_rows": len(table),
        "train_table_first_target": str(table.target_time_utc.min()),
        "train_table_last_target": str(table.target_time_utc.max()),
        "monthly_coverage": monthly,
        "features": features,
        "baseline_features": CALENDAR_FEATURES,
        "source_versions": source_versions,
        "folds": folds,
        "aggregate_backtest": aggregate,
        "final_fit_train_period": [str(final_train.target_time_utc.min()), str(final_train.target_time_utc.max())],
        "final_fit_calibration_period": [str(final_calibration.target_time_utc.min()), str(final_calibration.target_time_utc.max())],
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    print(f"Saved {len(table)} half-hour rows, five backtest folds, and final model in {args.output_dir}")


if __name__ == "__main__":
    main()

"""Train an exploratory 24-hour dispatch-down model from an approved forecast archive.

The input must contain forecasts captured before each decision time. This script
does not fetch or retain Azure Maps results; confirm the source's training rights
before creating the archive passed to --weather-input.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

try:
    from .train_real_baseline import calendar_features, fit_hurdle
except ImportError:
    from train_real_baseline import calendar_features, fit_hurdle


WEATHER_COLUMNS = (
    "wind_speed_mps",
    "wind_gust_mps",
    "wind_direction_deg",
    "cloud_cover_pct",
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_probability_pct",
)
REQUIRED_FORECAST_COLUMNS = (
    "provider", "location_id", "retrieved_at_utc", "valid_time_utc", "wind_speed_mps"
)


def prepare_weather_frame(
    labels: pd.DataFrame,
    forecasts: pd.DataFrame,
    *,
    location_id: str,
    horizon_hours: int = 24,
    max_age_hours: int = 6,
) -> tuple[pd.DataFrame, list[str]]:
    """Join the latest forecast available by the decision time to each label.

    An hourly value is assigned to the two half-hours within its UTC hour.
    This is a feature mapping, not a claim of half-hour weather precision.
    """
    if horizon_hours < 1 or max_age_hours < 1:
        raise ValueError("horizon_hours and max_age_hours must be positive")
    missing_labels = {"timestamp", "dispatch_down_total_mwh"} - set(labels)
    missing_forecasts = set(REQUIRED_FORECAST_COLUMNS) - set(forecasts)
    if missing_labels or missing_forecasts:
        raise ValueError(f"Missing columns: labels={sorted(missing_labels)}, forecasts={sorted(missing_forecasts)}")

    left = labels[["timestamp", "dispatch_down_total_mwh"]].copy()
    left["target_time_utc"] = pd.to_datetime(left.pop("timestamp"), utc=True)
    if left["target_time_utc"].duplicated().any():
        raise ValueError("Label timestamps must be unique")
    left["decision_time_utc"] = left["target_time_utc"] - pd.Timedelta(hours=horizon_hours)
    left["weather_valid_hour_utc"] = left["target_time_utc"].dt.floor("h")

    right = forecasts.loc[forecasts["location_id"].eq(location_id)].copy()
    if right.empty:
        raise ValueError(f"No weather rows for location_id={location_id!r}")
    if right["provider"].nunique() != 1:
        raise ValueError("Use one provider per training run")
    right["retrieved_at_utc"] = pd.to_datetime(right["retrieved_at_utc"], utc=True)
    right["valid_time_utc"] = pd.to_datetime(right["valid_time_utc"], utc=True)
    if right["valid_time_utc"].dt.minute.ne(0).any() or right["valid_time_utc"].dt.second.ne(0).any():
        raise ValueError("Forecast valid times must be hourly")
    if right.duplicated(["valid_time_utc", "retrieved_at_utc"]).any():
        raise ValueError("Duplicate forecast version for a valid hour")
    for col in WEATHER_COLUMNS:
        if col not in right:
            right[col] = np.nan
        right[col] = pd.to_numeric(right[col], errors="coerce")

    right = right.rename(columns={"valid_time_utc": "weather_valid_hour_utc"})
    right = right.sort_values("retrieved_at_utc")
    left = left.sort_values("decision_time_utc")
    frame = pd.merge_asof(
        left,
        right[["provider", "location_id", "retrieved_at_utc", "weather_valid_hour_utc", *WEATHER_COLUMNS]],
        left_on="decision_time_utc",
        right_on="retrieved_at_utc",
        by="weather_valid_hour_utc",
        direction="backward",
        tolerance=pd.Timedelta(hours=max_age_hours),
    )
    frame["wind_direction_sin"] = np.sin(np.deg2rad(frame["wind_direction_deg"]))
    frame["wind_direction_cos"] = np.cos(np.deg2rad(frame["wind_direction_deg"]))
    features = [col for col in WEATHER_COLUMNS if col != "wind_direction_deg"]
    features += ["wind_direction_sin", "wind_direction_cos"]
    features += calendar_features(frame, frame["target_time_utc"], prefix="target_")
    return frame.sort_values("target_time_utc").reset_index(drop=True), features


def train(
    labels_path: Path,
    weather_path: Path,
    output_dir: Path,
    *,
    location_id: str,
    horizon_hours: int = 24,
    max_age_hours: int = 6,
    threshold_mwh: float = 5.0,
    min_rows: int = 500,
) -> dict:
    labels = pd.read_csv(labels_path)
    forecasts = pd.read_csv(weather_path)
    frame, features = prepare_weather_frame(
        labels, forecasts, location_id=location_id,
        horizon_hours=horizon_hours, max_age_hours=max_age_hours,
    )
    covered = frame["retrieved_at_utc"].notna() & frame["wind_speed_mps"].notna()
    frame = frame.loc[covered & frame["dispatch_down_total_mwh"].notna()].copy()
    if len(frame) < min_rows:
        raise ValueError(
            f"Only {len(frame)} aligned labeled rows; need at least {min_rows}. "
            "Current Azure Maps forecasts cannot train against older labels."
        )
    split_index = int(len(frame) * 0.8)
    split = frame.iloc[split_index]["target_time_utc"].ceil("D")
    train_mask = frame["target_time_utc"].lt(split)
    test_mask = ~train_mask
    if train_mask.sum() < 100 or test_mask.sum() < 100:
        raise ValueError("Need at least 100 training and 100 test rows after the day-boundary split")
    features = [col for col in features if frame.loc[train_mask, col].notna().any()]
    train_events = frame.loc[train_mask, "dispatch_down_total_mwh"].gt(threshold_mwh)
    test_events = frame.loc[test_mask, "dispatch_down_total_mwh"].gt(threshold_mwh)
    if train_events.nunique() < 2 or test_events.nunique() < 2 or train_events.sum() < 20:
        raise ValueError("Insufficient positive and negative events for a meaningful holdout")

    occurrence, volume, scores = fit_hurdle(
        frame, features, "dispatch_down_total_mwh", train_mask, test_mask, threshold_mwh
    )
    calendar_features_only = [col for col in features if col.startswith("target_")]
    _, _, calendar_scores = fit_hurdle(
        frame, calendar_features_only, "dispatch_down_total_mwh",
        train_mask, test_mask, threshold_mwh,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "features": features,
        "provider": str(frame["provider"].iloc[0]),
        "location_id": location_id,
        "horizon_hours": horizon_hours,
        "max_age_hours": max_age_hours,
        "threshold_mwh": threshold_mwh,
        "weather_valid_hour_mapping": "floor target half-hour to UTC hour",
    }
    joblib.dump({"model": occurrence, **metadata}, output_dir / "weather_occurrence.joblib")
    joblib.dump({"model": volume, **metadata}, output_dir / "weather_volume.joblib")
    report = {
        "product": "exploratory weather-and-calendar dispatch-down forecast",
        "warning": "Single chronological holdout only; validate point-in-time capture and source rights before any performance claim.",
        "matched_rows": len(frame),
        "forecast_archive_start_utc": frame["retrieved_at_utc"].min().isoformat(),
        "forecast_archive_end_utc": frame["retrieved_at_utc"].max().isoformat(),
        "test_start_utc": split.isoformat(),
        "feature_count": len(features),
        "source": metadata,
        "metrics": scores,
        "calendar_only_metrics": calendar_scores,
    }
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-input", type=Path, default=Path("data/processed/dispatch_down_labels_ie_2021_2026.csv"))
    parser.add_argument("--weather-input", type=Path, required=True, help="Approved point-in-time forecast archive CSV")
    parser.add_argument("--location-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--horizon-hours", type=int, default=24)
    parser.add_argument("--max-age-hours", type=int, default=6)
    parser.add_argument("--event-threshold-mwh", type=float, default=5.0)
    args = parser.parse_args()
    report = train(
        args.labels_input, args.weather_input, args.output_dir,
        location_id=args.location_id, horizon_hours=args.horizon_hours,
        max_age_hours=args.max_age_hours, threshold_mwh=args.event_threshold_mwh,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

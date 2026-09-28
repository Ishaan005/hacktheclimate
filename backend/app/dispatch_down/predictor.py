from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from scripts.train_real_baseline import prepare_one_hour_frame

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data" / "processed" / "training_table_labeled_jan2026.csv"
ARTIFACTS = REPO_ROOT / "artifacts" / "real_baseline"
HORIZON_HOURS = 1


def _normalise_timestamp(value: str) -> pd.Timestamp:
    """Return a timezone-naive UTC timestamp matching the included CSV data."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return timestamp


class DispatchDownPredictor:
    """One-hour-ahead dispatch-down predictor using the included baseline artifacts."""

    def __init__(self) -> None:
        if not DATA_PATH.exists():
            raise FileNotFoundError(DATA_PATH)

        source = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
        self.frame, self.features = prepare_one_hour_frame(source)
        self.occurrence = joblib.load(ARTIFACTS / "forecast_1h_occurrence.joblib")
        self.volume = joblib.load(ARTIFACTS / "forecast_1h_volume.joblib")

        if self.occurrence["features"] != self.features or self.volume["features"] != self.features:
            raise ValueError("Saved model features do not match the current prediction pipeline.")

    def predict(self, target_timestamp: str) -> dict:
        """Predict whether material dispatch-down occurs one hour before a target time."""
        target = _normalise_timestamp(target_timestamp)
        row = self.frame.loc[self.frame["target_1h_timestamp"] == target]
        if row.empty:
            raise ValueError("No historical input data is available for that target timestamp.")

        probability = float(self.occurrence["model"].predict_proba(row[self.features])[:, 1][0])
        conditional_volume = float(max(self.volume["model"].predict(row[self.features])[0], 0.0))
        expected_mwh = probability * conditional_volume

        return {
            "mode": "historical_replay",
            "input_timestamp": row.iloc[0]["timestamp"].isoformat(),
            "target_timestamp": target.isoformat(),
            "horizon_hours": HORIZON_HOURS,
            "risk": "high" if probability >= 0.7 else "elevated" if probability >= 0.3 else "low",
            "event_probability": probability,
            "expected_dispatch_down_mwh": expected_mwh,
            "limitations": [
                "This is a historical one-hour-ahead replay, not a live forecast.",
                "It forecasts national dispatch-down risk, not a specific transmission line or location.",
            ],
        }

    def predict_day(self, target_timestamp: str) -> dict:
        """Return every half-hourly replay prediction on the UTC day of a target time."""
        target = _normalise_timestamp(target_timestamp)
        day_start = target.normalize()
        targets = self.frame["target_1h_timestamp"]
        rows = self.frame.loc[(targets >= day_start) & (targets < day_start + pd.Timedelta(days=1))]
        if rows.empty:
            raise ValueError("No historical input data is available for that day.")
        rows = rows.sort_values("target_1h_timestamp")
        probability = self.occurrence["model"].predict_proba(rows[self.features])[:, 1]
        volume = self.volume["model"].predict(rows[self.features]).clip(min=0.0)
        points = [
            {
                "target_timestamp": ts.isoformat(),
                "event_probability": float(p),
                "expected_dispatch_down_mwh": float(p * v),
            }
            for ts, p, v in zip(rows["target_1h_timestamp"], probability, volume)
        ]
        return {
            "mode": "historical_replay",
            "date": day_start.date().isoformat(),
            "horizon_hours": HORIZON_HOURS,
            "points": points,
        }


@lru_cache(maxsize=1)
def get_dispatch_down_predictor() -> DispatchDownPredictor:
    """Load the data and saved models once per API process."""
    return DispatchDownPredictor()

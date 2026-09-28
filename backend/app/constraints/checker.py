"""Historical replay of the forward national constraint model (artifacts/forward_constraint)."""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

import scripts.forward_constraint as forward_constraint
from scripts.forward_constraint import HurdleForecastBundle, prepare_forecast_frame

# The bundles were pickled while `scripts/` was on sys.path, so joblib looks for a
# top-level `forward_constraint` module. Alias it so loading works from the API.
sys.modules.setdefault("forward_constraint", forward_constraint)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data/processed/training_table_eirgrid_2026_jan_aug.csv"
ARTIFACTS = REPO_ROOT / "artifacts/forward_constraint"
SUPPORTED_HORIZONS = (1, 4, 6, 12, 24)
HIGH_RISK, ELEVATED_RISK = 0.7, 0.3  # same bands as the dispatch-down predictor

LIMITATIONS = [
    "Historical replay, not a live operational forecast.",
    "Uses the final-fit model trained on January to August 2026, so replayed times were seen in training and will look better than a true forecast.",
    "National constraint total only; separate from curtailment and total dispatch-down, and it does not identify a line or location.",
    "The 80% range comes from quantile models and is not calibrated.",
]


def _utc_naive(value: str) -> pd.Timestamp:
    """Parse ISO time; convert any timezone to UTC and drop it to match the CSV."""
    try:
        ts = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Could not read timestamp {value!r}. Use ISO format, e.g. 2026-01-24T01:00:00Z.") from exc
    return ts.tz_convert("UTC").tz_localize(None) if ts.tzinfo is not None else ts


def risk_level(probability: float) -> str:
    if probability >= HIGH_RISK:
        return "high"
    if probability >= ELEVATED_RISK:
        return "elevated"
    return "low"


class ConstraintChecker:
    """Loads the data once and each horizon's frame and model on first use."""

    def __init__(self, data_path: Path = DATA_PATH, artifacts: Path = ARTIFACTS) -> None:
        if not data_path.exists():
            raise FileNotFoundError(data_path)
        self._source = pd.read_csv(data_path, parse_dates=["timestamp"])
        self._artifacts = artifacts
        self._horizons: dict[int, tuple[pd.DataFrame, HurdleForecastBundle]] = {}

    def _horizon(self, horizon_hours: int) -> tuple[pd.DataFrame, HurdleForecastBundle]:
        if horizon_hours not in SUPPORTED_HORIZONS:
            raise ValueError(f"Supported horizons are {', '.join(map(str, SUPPORTED_HORIZONS))} hours.")
        if horizon_hours not in self._horizons:
            model_path = self._artifacts / f"model_{horizon_hours}h_final_fit.joblib"
            if not model_path.exists():
                raise FileNotFoundError(model_path)
            model = HurdleForecastBundle.load(model_path)
            frame, features, _ = prepare_forecast_frame(self._source, horizon_hours)
            if list(model.feature_names) != [f for f in model.feature_names if f in features]:
                raise ValueError(f"The {horizon_hours}h model expects features the data pipeline no longer builds.")
            frame = frame.dropna(subset=["target_timestamp"]).set_index("target_timestamp", drop=False)
            self._horizons[horizon_hours] = (frame, model)
        return self._horizons[horizon_hours]

    def available_range(self, horizon_hours: int) -> tuple[str, str]:
        frame, _ = self._horizon(horizon_hours)
        return frame.index.min().isoformat(), frame.index.max().isoformat()

    def check(self, target_timestamp: str, horizon_hours: int = 1) -> dict:
        target = _utc_naive(target_timestamp)
        frame, model = self._horizon(horizon_hours)

        if target not in frame.index:
            start, end = self.available_range(horizon_hours)
            hint = " Use a time on the hour or half hour." if target.minute not in (0, 30) or target.second else ""
            raise ValueError(f"No replay data for {target.isoformat()} at {horizon_hours}h ahead. Available: {start} to {end} UTC.{hint}")

        row = frame.loc[[target]]
        prediction = model.predict(row)
        probability = float(prediction["event_probability"][0])
        expected = float(prediction["expected_constraint_mwh"][0])
        if not (math.isfinite(probability) and math.isfinite(expected)):
            raise ValueError("The model could not produce a forecast for that time (missing inputs).")

        return {
            "mode": "historical_replay",
            "target": "constraint_mwh",
            "event_definition": f"National constraint above {model.threshold_mwh:g} MWh in the half-hour",
            "input_timestamp": row.iloc[0]["timestamp"].isoformat(),
            "target_timestamp": target.isoformat(),
            "horizon_hours": horizon_hours,
            "risk_level": risk_level(probability),
            "event_probability": probability,
            "expected_constraint_mwh": expected,
            "interval_80_mwh": {
                "low": float(prediction["interval_80_lower_mwh"][0]),
                "high": float(prediction["interval_80_upper_mwh"][0]),
            },
            "limitations": LIMITATIONS,
        }


@lru_cache(maxsize=1)
def get_constraint_checker() -> ConstraintChecker:
    return ConstraintChecker()

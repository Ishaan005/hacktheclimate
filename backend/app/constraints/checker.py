from functools import lru_cache
from pathlib import Path

import pandas as pd

from scripts.forward_constraint import HurdleForecastBundle, prepare_forecast_frame

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data/processed/training_table_eirgrid_2026_jan_aug.csv"
ARTIFACTS = REPO_ROOT / "artifacts/forward_constraint"


class ConstraintChecker:
    def check(self, target_timestamp: str, horizon_hours: int) -> dict:
        target = pd.Timestamp(target_timestamp)

        source = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
        frame, features, _ = prepare_forecast_frame(source, horizon_hours)

        row = frame.loc[frame["target_timestamp"] == target]
        if row.empty:
            raise ValueError("No historical data is available for that timestamp.")

        model_path = ARTIFACTS / f"model_{horizon_hours}h_final_fit.joblib"
        model = HurdleForecastBundle.load(model_path)

        prediction = model.predict(row[features])

        probability = float(prediction["event_probability"][0])
        expected_mwh = float(prediction["expected_constraint_mwh"][0])

        return {
            "mode": "historical_replay",
            "target_timestamp": target.isoformat(),
            "input_timestamp": row.iloc[0]["timestamp"].isoformat(),
            "horizon_hours": horizon_hours,
            "risk_level": (
                "high" if probability >= 0.7
                else "medium" if probability >= 0.3
                else "low"
            ),
            "event_probability": probability,
            "expected_constraint_mwh": expected_mwh,
            "interval_80_mwh": {
                "low": float(prediction["interval_80_lower_mwh"][0]),
                "high": float(prediction["interval_80_upper_mwh"][0]),
            },
            "limitations": [
                "Historical replay, not a live operational forecast.",
                "National estimate only; it does not identify a constrained line or location.",
            ],
        }


@lru_cache(maxsize=1)
def get_constraint_checker() -> ConstraintChecker:
    return ConstraintChecker()

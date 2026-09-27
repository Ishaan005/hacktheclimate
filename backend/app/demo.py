from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.train_real_baseline import prepare_one_hour_frame

from .optimizer import FlexibleAsset, optimize_absorption

router = APIRouter(prefix="/v1/demo", tags=["retrospective demo"])
DATA = Path("data/processed/training_table_labeled_jan2026.csv")
ARTIFACTS = Path("artifacts/real_baseline")
HOLDOUT_START = pd.Timestamp("2026-01-24")
HOLDOUT_END = pd.Timestamp("2026-02-01")


class AssetSpec(BaseModel):
    name: str = Field(min_length=1)
    max_power_mw: float = Field(gt=0, allow_inf_nan=False)
    energy_required_mwh: float = Field(gt=0, allow_inf_nan=False)
    available: list[bool]


class AbsorptionRequest(BaseModel):
    start_target: datetime = datetime(2026, 1, 24)
    intervals: int = Field(default=48, ge=1, le=48)
    assets: list[AssetSpec] = Field(min_length=1, max_length=10)


@lru_cache(maxsize=1)
def _holdout_predictions() -> pd.DataFrame:
    if not DATA.exists():
        raise FileNotFoundError(DATA)
    occurrence_path = ARTIFACTS / "forecast_1h_occurrence.joblib"
    volume_path = ARTIFACTS / "forecast_1h_volume.joblib"
    occurrence = joblib.load(occurrence_path)
    volume = joblib.load(volume_path)

    source = pd.read_csv(DATA, parse_dates=["timestamp"])
    frame, features = prepare_one_hour_frame(source)
    if occurrence["features"] != features or volume["features"] != features:
        raise ValueError("Saved 1-hour model features do not match the current training pipeline.")

    probability = occurrence["model"].predict_proba(frame[features])[:, 1]
    conditional_volume = np.maximum(volume["model"].predict(frame[features]), 0)
    frame["event_probability"] = probability
    frame["expected_dispatch_down_mwh"] = probability * conditional_volume
    frame = frame.loc[
        frame["target_1h_timestamp"].ge(HOLDOUT_START)
        & frame["target_1h_timestamp"].lt(HOLDOUT_END)
        & frame["target_1h_mwh"].notna(),
        ["timestamp", "target_1h_timestamp", "target_1h_mwh", "event_probability", "expected_dispatch_down_mwh"],
    ].copy()
    return frame.set_index("target_1h_timestamp", verify_integrity=True)


@router.post("/absorption")
def demo_absorption(request: AbsorptionRequest):
    """A retrospective scheduling scenario, not a validated avoided-DD estimate."""
    target_start = pd.Timestamp(request.start_target)
    if target_start.tzinfo is not None:
        target_start = target_start.tz_convert("UTC").tz_localize(None)
    if target_start.minute not in (0, 30) or target_start.second or target_start.microsecond:
        raise HTTPException(422, "start_target must be on a UTC half-hour boundary")
    if len({asset.name for asset in request.assets}) != len(request.assets):
        raise HTTPException(422, "Asset names must be unique")
    if any(len(asset.available) != request.intervals for asset in request.assets):
        raise HTTPException(422, "Each asset's availability list must match intervals")

    target_times = pd.date_range(target_start, periods=request.intervals, freq="30min")
    if target_times[0] < HOLDOUT_START or target_times[-1] >= HOLDOUT_END:
        raise HTTPException(422, "Choose target half-hours within the 24–31 January 2026 holdout")

    try:
        selected = _holdout_predictions().reindex(target_times)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
    if selected["expected_dispatch_down_mwh"].isna().any():
        raise HTTPException(422, "The requested window has missing model inputs or targets")

    expected_mwh = selected["expected_dispatch_down_mwh"].to_numpy()
    assets = [FlexibleAsset(a.name, a.max_power_mw, a.energy_required_mwh, a.available) for a in request.assets]
    schedule = optimize_absorption((expected_mwh / 0.5).tolist(), assets)
    intervals = [
        {
            "target_timestamp": timestamp.isoformat(),
            "input_timestamp": row["timestamp"].isoformat(),
            "event_probability_gt_5_mwh": float(row["event_probability"]),
            "predicted_dispatch_down_mwh": float(row["expected_dispatch_down_mwh"]),
            "observed_dispatch_down_mwh": float(row["target_1h_mwh"]),
        }
        for timestamp, row in selected.iterrows()
    ]
    return {
        "scenario": "retrospective_1h_operational",
        "assumption": "Treating every predicted dispatch-down MWh as locally absorbable is an unvalidated upper bound. The schedule is illustrative; absorbed MWh is not proven avoided dispatch-down.",
        "interval_hours": 0.5,
        "predicted_dispatch_down_mwh": float(expected_mwh.sum()),
        "observed_dispatch_down_mwh": float(selected["target_1h_mwh"].sum()),
        "schedule": schedule,
        "intervals": intervals,
    }

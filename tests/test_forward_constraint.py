"""Unit tests for the forward-looking national constraint forecast model."""

import numpy as np
import pandas as pd
import pytest

from scripts.forward_constraint import (
    calendar_encodings,
    expected_calibration_error,
    prepare_forecast_frame,
    train_hurdle_bundle,
)


def _synthetic_eirgrid_frame(n_rows: int = 200, freq: str = "30min") -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01 00:00:00", periods=n_rows, freq=freq)
    rng = np.random.RandomState(42)
    demand = rng.uniform(2000, 4500, size=n_rows)
    wind_avail = rng.uniform(200, 3000, size=n_rows)
    wind_gen = np.minimum(wind_avail, demand * 0.5)
    constraint = rng.exponential(scale=30.0, size=n_rows) * (rng.uniform(0, 1, size=n_rows) > 0.4)
    curtailment = rng.exponential(scale=20.0, size=n_rows) * (rng.uniform(0, 1, size=n_rows) > 0.6)

    return pd.DataFrame({
        "timestamp": timestamps,
        "eirgrid_ie_demand_mw": demand,
        "eirgrid_ie_wind_availability_mw": wind_avail,
        "eirgrid_ie_wind_generation_mw": wind_gen,
        "eirgrid_snsp_pct": rng.uniform(20, 75, size=n_rows),
        "constraint_mwh": constraint,
        "curtailment_mwh": curtailment,
    })


def test_prepare_forecast_frame_alignment_and_gap_exclusion():
    # 4 rows: 00:00, 00:30, 01:00, and a gap to 02:30
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-01-01 00:00:00",
            "2026-01-01 00:30:00",
            "2026-01-01 01:00:00",
            "2026-01-01 02:30:00",
        ]),
        "eirgrid_ie_demand_mw": [3000, 3100, 3200, 3300],
        "eirgrid_ie_wind_availability_mw": [1000, 1100, 1200, 1300],
        "constraint_mwh": [10.0, 20.0, 30.0, 40.0],
        "curtailment_mwh": [5.0, 6.0, 7.0, 8.0],
    })

    # Horizon 1h (2 steps ahead)
    frame, features, cal_lag = prepare_forecast_frame(df, horizon_hours=1.0, threshold_mwh=5.0)

    # Row 0: timestamp 00:00 -> target 01:00 (exact match)
    assert frame.loc[0, "target_timestamp"] == pd.Timestamp("2026-01-01 01:00:00")
    assert frame.loc[0, "target_constraint_mwh"] == 30.0
    assert frame.loc[0, "target_constraint_event"] == 1.0

    # Row 1: timestamp 00:30 -> 2 steps ahead is 02:30 (which is 2 hours away, not 1 hour!)
    # Should be excluded as NaN due to exact_match check
    assert pd.isna(frame.loc[1, "target_constraint_mwh"])
    assert pd.isna(frame.loc[1, "target_constraint_event"])

    # Row 2 & 3: shift exceeds dataframe length -> NaN
    assert pd.isna(frame.loc[2, "target_constraint_mwh"])
    assert pd.isna(frame.loc[3, "target_constraint_mwh"])


def test_forecast_features_are_strictly_pre_decision():
    df = _synthetic_eirgrid_frame(n_rows=100)
    horizon_hours = 4.0  # 8 intervals
    frame, features, cal_lag = prepare_forecast_frame(df, horizon_hours=horizon_hours)

    # Check that all physical features are suffixed with _t0 or rolling/delta _t0
    for feat in features:
        if feat.startswith("target_"):
            # Target features should only be calendar features
            assert any(feat.endswith(s) for s in ["sin", "cos", "is_weekend"])
        else:
            assert "_t0" in feat

    # Minimal calendar lag baseline features should contain only calendar + t0 constraint lag
    assert "constraint_mwh_t0" in cal_lag
    for feat in cal_lag:
        assert feat.startswith("target_") or feat == "constraint_mwh_t0"


def test_no_overlapping_target_times_in_chronological_split():
    df = _synthetic_eirgrid_frame(n_rows=200)
    horizon_hours = 1.0
    frame, features, _ = prepare_forecast_frame(df, horizon_hours=horizon_hours)
    valid = frame["target_constraint_mwh"].notna()

    split_time = pd.Timestamp("2026-01-03 00:00:00")
    train_mask = valid & frame["target_timestamp"].lt(split_time)
    test_mask = valid & frame["target_timestamp"].ge(split_time)

    train_targets = frame.loc[train_mask, "target_timestamp"]
    test_targets = frame.loc[test_mask, "target_timestamp"]

    # Maximum training target must be strictly less than split_time
    assert train_targets.max() < split_time
    # Minimum test target must be at or after split_time
    assert test_targets.min() >= split_time
    # Intersection of target timestamps must be completely empty
    assert len(set(train_targets).intersection(set(test_targets))) == 0


def test_hurdle_bundle_predicts_valid_ranges_and_non_negative_bounds():
    df = _synthetic_eirgrid_frame(n_rows=300)
    horizon_hours = 1.0
    frame, features, cal_lag = prepare_forecast_frame(df, horizon_hours=horizon_hours)
    valid = frame["target_constraint_mwh"].notna()

    split_idx = 200
    train_df = frame[valid].iloc[:split_idx]
    test_df = frame[valid].iloc[split_idx:]

    bundle = train_hurdle_bundle(
        train_df=train_df,
        features=features,
        cal_lag_features=cal_lag,
        horizon_hours=horizon_hours,
        threshold_mwh=5.0,
    )

    preds = bundle.predict(test_df)

    # 1. Event probabilities in [0, 1]
    assert np.all(preds["event_probability"] >= 0.0)
    assert np.all(preds["event_probability"] <= 1.0)

    # 2. Conditional volume and expected MWh >= 0
    assert np.all(preds["conditional_volume_mwh"] >= 0.0)
    assert np.all(preds["expected_constraint_mwh"] >= 0.0)

    # 3. Prediction intervals: low >= 0 and low <= high
    assert np.all(preds["interval_80_lower_mwh"] >= 0.0)
    assert np.all(preds["interval_80_lower_mwh"] <= preds["interval_80_upper_mwh"])

    assert np.all(preds["interval_90_lower_mwh"] >= 0.0)
    assert np.all(preds["interval_90_lower_mwh"] <= preds["interval_90_upper_mwh"])


def test_expected_calibration_error_computation():
    y_true = np.array([1, 1, 0, 0, 1, 0, 1, 0])
    # Perfectly calibrated case: prob = true label
    ece_perfect, bins_perfect = expected_calibration_error(y_true, y_true.astype(float), n_bins=5)
    assert ece_perfect == pytest.approx(0.0, abs=1e-5)

    # Partially calibrated case
    y_prob = np.array([0.9, 0.8, 0.2, 0.1, 0.7, 0.3, 0.85, 0.15])
    ece, bins = expected_calibration_error(y_true, y_prob, n_bins=5)
    assert 0.0 <= ece <= 1.0
    assert len(bins) == 5

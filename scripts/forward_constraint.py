"""Forward-looking national constraint forecast modeling.

Trains an event-probability model and non-negative conditional-volume model
on strictly forecast-safe features to predict national constraint MWh, keeping
constraint_mwh separate from system-wide curtailment_mwh.

Forecast-safe principle:
For a prediction target at timestamp T at lead time H hours, the forecast issue
time is t_0 = T - H. All grid and market measurements are strictly sampled at
or before t_0. Only deterministic calendar features are evaluated at target time T.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_absolute_error,
    precision_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)

BASE_SYSTEM_COLUMNS = [
    "eirgrid_ie_demand_mw",
    "eirgrid_ie_wind_availability_mw",
    "eirgrid_ie_wind_generation_mw",
    "eirgrid_ie_solar_availability_mw",
    "eirgrid_ie_solar_generation_mw",
    "eirgrid_ie_hydro_mw",
    "eirgrid_ewic_ic_mw",
    "eirgrid_greenlink_ic_mw",
    "eirgrid_moyle_ic_mw",
    "eirgrid_interjurisdictional_flow_mw",
    "eirgrid_snsp_pct",
    "eirgrid_ai_demand_mw",
    "eirgrid_ai_generation_mw",
    "eirgrid_ai_wind_availability_mw",
    "eirgrid_ai_oversupply_mw",
    "curtailment_mwh",
    "constraint_mwh",
]


def calendar_encodings(timestamp: pd.Series, prefix: str = "target_") -> pd.DataFrame:
    """Deterministic cyclical and day-type features for future target timestamps."""
    hour = timestamp.dt.hour + timestamp.dt.minute / 60.0
    dow = timestamp.dt.dayofweek
    month = timestamp.dt.month
    return pd.DataFrame(
        {
            f"{prefix}hour_sin": np.sin(2 * np.pi * hour / 24.0),
            f"{prefix}hour_cos": np.cos(2 * np.pi * hour / 24.0),
            f"{prefix}dow_sin": np.sin(2 * np.pi * dow / 7.0),
            f"{prefix}dow_cos": np.cos(2 * np.pi * dow / 7.0),
            f"{prefix}month_sin": np.sin(2 * np.pi * month / 12.0),
            f"{prefix}month_cos": np.cos(2 * np.pi * month / 12.0),
            f"{prefix}is_weekend": (dow >= 5).astype(float),
        },
        index=timestamp.index,
    )


def prepare_forecast_frame(
    raw_df: pd.DataFrame,
    horizon_hours: float,
    threshold_mwh: float = 5.0,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Build strictly forecast-safe features for a given horizon H (in hours).

    Each row represents a decision point at `timestamp` (t_0) forecasting
    `target_timestamp` (t_0 + horizon_hours).
    All physical measurements are strictly measured at or before t_0.

    Returns:
        frame: aligned DataFrame with forecast-safe features, target, and masks
        feature_cols: full feature list for the ML model
        cal_lag_cols: minimal feature list for the calendar/lag baseline
    """
    df = raw_df.sort_values("timestamp").reset_index(drop=True).copy()
    step_intervals = int(round(horizon_hours * 2))
    if step_intervals <= 0:
        raise ValueError(f"horizon_hours must be > 0, got {horizon_hours}")

    # Explicit target alignment: target is exactly horizon_hours ahead
    df["target_timestamp"] = df["timestamp"].shift(-step_intervals)
    df["target_constraint_mwh"] = df["constraint_mwh"].shift(-step_intervals)

    # Exclude rows where the target timestamp does not match the exact expected horizon
    expected_delta = pd.Timedelta(hours=horizon_hours)
    exact_match = df["target_timestamp"].eq(df["timestamp"] + expected_delta)
    df.loc[~exact_match, "target_constraint_mwh"] = np.nan

    # 1. Deterministic calendar features for the FUTURE target timestamp
    target_cal = calendar_encodings(df["target_timestamp"], prefix="target_")
    for col in target_cal.columns:
        df[col] = target_cal[col]

    cal_cols = list(target_cal.columns)

    # 2. Decision-time (t_0) physical system features
    available_sys = [c for c in BASE_SYSTEM_COLUMNS if c in df.columns]
    feature_cols = list(cal_cols)

    for col in available_sys:
        feature_name = f"{col}_t0"
        df[feature_name] = df[col]
        feature_cols.append(feature_name)

    # 3. Decision-time historical dynamics (deltas strictly before t_0)
    # 1-hour delta: x(t_0) - x(t_0 - 1h) -> shift 2 intervals back
    # 4-hour delta: x(t_0) - x(t_0 - 4h) -> shift 8 intervals back
    # 24-hour delta: x(t_0) - x(t_0 - 24h) -> shift 48 intervals back
    delta_cols = [
        "eirgrid_ie_demand_mw",
        "eirgrid_ie_wind_availability_mw",
        "eirgrid_snsp_pct",
        "constraint_mwh",
    ]
    for col in delta_cols:
        if col not in df.columns:
            continue
        # Check continuity for delta
        is_1h_prior = df["timestamp"].sub(df["timestamp"].shift(2)).eq(pd.Timedelta(hours=1))
        d1 = f"{col}_delta_1h_t0"
        df[d1] = (df[col] - df[col].shift(2)).where(is_1h_prior)
        feature_cols.append(d1)

        is_4h_prior = df["timestamp"].sub(df["timestamp"].shift(8)).eq(pd.Timedelta(hours=4))
        d4 = f"{col}_delta_4h_t0"
        df[d4] = (df[col] - df[col].shift(8)).where(is_4h_prior)
        feature_cols.append(d4)

        is_24h_prior = df["timestamp"].sub(df["timestamp"].shift(48)).eq(pd.Timedelta(hours=24))
        d24 = f"{col}_delta_24h_t0"
        df[d24] = (df[col] - df[col].shift(48)).where(is_24h_prior)
        feature_cols.append(d24)

    # 4. Decision-time rolling historical statistics (strictly backwards from t_0)
    # rolling 6h (12 intervals) and rolling 24h (48 intervals)
    for col in ["eirgrid_ie_wind_availability_mw", "eirgrid_ie_demand_mw", "constraint_mwh"]:
        if col not in df.columns:
            continue
        r6_mean = f"{col}_roll6h_mean_t0"
        r24_mean = f"{col}_roll24h_mean_t0"
        r24_max = f"{col}_roll24h_max_t0"

        df[r6_mean] = df[col].rolling(12, min_periods=6).mean()
        df[r24_mean] = df[col].rolling(48, min_periods=24).mean()
        df[r24_max] = df[col].rolling(48, min_periods=24).max()

        feature_cols.extend([r6_mean, r24_mean, r24_max])

    # Minimal feature set for calendar/lag baseline: target calendar + t_0 constraint lag
    cal_lag_cols = list(cal_cols) + ["constraint_mwh_t0"]

    # Target event indicator
    df["target_constraint_event"] = (df["target_constraint_mwh"] > threshold_mwh).astype(float)
    df.loc[df["target_constraint_mwh"].isna(), "target_constraint_event"] = np.nan

    return df, feature_cols, cal_lag_cols


def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate Expected Calibration Error (ECE) and reliability bin statistics."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    ece = 0.0
    n = len(y_true)
    reliability_bins = []

    for b in range(n_bins):
        mask = bin_indices == b
        count = int(mask.sum())
        bin_lower = float(bins[b])
        bin_upper = float(bins[b + 1])
        if count > 0:
            mean_prob = float(np.mean(y_prob[mask]))
            emp_freq = float(np.mean(y_true[mask]))
            ece += (count / n) * abs(mean_prob - emp_freq)
            reliability_bins.append({
                "bin": b,
                "bin_lower": round(bin_lower, 2),
                "bin_upper": round(bin_upper, 2),
                "count": count,
                "mean_predicted_prob": round(mean_prob, 4),
                "empirical_event_rate": round(emp_freq, 4),
                "calibration_gap": round(abs(mean_prob - emp_freq), 4),
            })
        else:
            reliability_bins.append({
                "bin": b,
                "bin_lower": round(bin_lower, 2),
                "bin_upper": round(bin_upper, 2),
                "count": 0,
                "mean_predicted_prob": None,
                "empirical_event_rate": None,
                "calibration_gap": None,
            })

    return float(ece), reliability_bins


@dataclass
class HurdleForecastBundle:
    """Trained hurdle model components with prediction intervals."""
    horizon_hours: float
    threshold_mwh: float
    feature_names: list[str]
    cal_lag_feature_names: list[str]
    clf: HistGradientBoostingClassifier
    reg: HistGradientBoostingRegressor
    q_low_80: HistGradientBoostingRegressor
    q_high_80: HistGradientBoostingRegressor
    q_low_90: HistGradientBoostingRegressor
    q_high_90: HistGradientBoostingRegressor
    cal_lag_clf: HistGradientBoostingClassifier
    cal_lag_reg: HistGradientBoostingRegressor
    train_mean_mwh: float

    def predict(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Generate point forecasts, expected MWh, and calibrated uncertainty bounds."""
        X_feat = X[self.feature_names]
        prob = self.clf.predict_proba(X_feat)[:, 1]
        cond_vol = np.maximum(self.reg.predict(X_feat), 0.0)
        expected_mwh = prob * cond_vol

        # Quantile predictions lower-bounded at 0
        low_80 = np.maximum(self.q_low_80.predict(X_feat), 0.0)
        high_80 = np.maximum(self.q_high_80.predict(X_feat), low_80)

        low_90 = np.maximum(self.q_low_90.predict(X_feat), 0.0)
        high_90 = np.maximum(self.q_high_90.predict(X_feat), low_90)

        return {
            "event_probability": prob,
            "conditional_volume_mwh": cond_vol,
            "expected_constraint_mwh": expected_mwh,
            "interval_80_lower_mwh": low_80,
            "interval_80_upper_mwh": high_80,
            "interval_90_lower_mwh": low_90,
            "interval_90_upper_mwh": high_90,
        }

    def predict_baseline(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Generate calendar/lag baseline predictions."""
        X_base = X[self.cal_lag_feature_names]
        prob = self.cal_lag_clf.predict_proba(X_base)[:, 1]
        cond_vol = np.maximum(self.cal_lag_reg.predict(X_base), 0.0)
        return {
            "baseline_event_probability": prob,
            "baseline_expected_mwh": prob * cond_vol,
        }

    def save(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)

    @classmethod
    def load(cls, path: Path) -> HurdleForecastBundle:
        return joblib.load(path)


def train_hurdle_bundle(
    train_df: pd.DataFrame,
    features: list[str],
    cal_lag_features: list[str],
    horizon_hours: float,
    threshold_mwh: float = 5.0,
    random_state: int = 42,
) -> HurdleForecastBundle:
    """Train the hurdle components and quantile uncertainty regressors strictly on training data."""
    X_train = train_df[features]
    y_train = train_df["target_constraint_mwh"].to_numpy()
    e_train = (y_train > threshold_mwh).astype(int)

    # 1. Main Hurdle Classifier
    clf = HistGradientBoostingClassifier(
        max_depth=5,
        learning_rate=0.05,
        max_iter=120,
        min_samples_leaf=20,
        random_state=random_state,
    )
    clf.fit(X_train, e_train)

    # 2. Main Non-negative Conditional Volume Regressor (trained strictly on positive events)
    pos_mask = y_train > threshold_mwh
    if pos_mask.sum() < 20:
        raise ValueError(f"Insufficient positive training events ({pos_mask.sum()}) to fit volume model.")

    reg = HistGradientBoostingRegressor(
        max_depth=5,
        learning_rate=0.05,
        max_iter=120,
        min_samples_leaf=20,
        random_state=random_state,
    )
    reg.fit(train_df.loc[pos_mask, features], y_train[pos_mask])

    # 3. Calibrated Uncertainty: Quantile regressors for 80% (q=0.10, 0.90) and 90% (q=0.05, 0.95)
    q_low_80 = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.10, max_depth=4, learning_rate=0.05, max_iter=80, random_state=random_state
    ).fit(X_train, y_train)

    q_high_80 = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.90, max_depth=4, learning_rate=0.05, max_iter=80, random_state=random_state
    ).fit(X_train, y_train)

    q_low_90 = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.05, max_depth=4, learning_rate=0.05, max_iter=80, random_state=random_state
    ).fit(X_train, y_train)

    q_high_90 = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.95, max_depth=4, learning_rate=0.05, max_iter=80, random_state=random_state
    ).fit(X_train, y_train)

    # 4. Minimal Calendar/Lag Baseline model
    cal_lag_clf = HistGradientBoostingClassifier(
        max_depth=4, learning_rate=0.05, max_iter=80, random_state=random_state
    ).fit(train_df[cal_lag_features], e_train)

    cal_lag_reg = HistGradientBoostingRegressor(
        max_depth=4, learning_rate=0.05, max_iter=80, random_state=random_state
    ).fit(train_df.loc[pos_mask, cal_lag_features], y_train[pos_mask])

    return HurdleForecastBundle(
        horizon_hours=horizon_hours,
        threshold_mwh=threshold_mwh,
        feature_names=features,
        cal_lag_feature_names=cal_lag_features,
        clf=clf,
        reg=reg,
        q_low_80=q_low_80,
        q_high_80=q_high_80,
        q_low_90=q_low_90,
        q_high_90=q_high_90,
        cal_lag_clf=cal_lag_clf,
        cal_lag_reg=cal_lag_reg,
        train_mean_mwh=float(np.mean(y_train)),
    )


def evaluate_forecast_bundle(
    bundle: HurdleForecastBundle,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    """Comprehensive evaluation against all acceptance criteria:

    - Event prevalence
    - PR-AUC, ROC-AUC, Brier score, ECE
    - MWh error (MAE, RMSE) vs simple baselines (Zero, Train-mean, Calendar/Lag)
    - Uncertainty coverage and interval widths for 80% and 90% intervals
    - Honest assessment of improvement vs calendar/lag baseline.
    """
    y_test = test_df["target_constraint_mwh"].to_numpy()
    e_test = (y_test > bundle.threshold_mwh).astype(int)
    n_test = len(y_test)

    # Model predictions
    preds = bundle.predict(test_df)
    p = preds["event_probability"]
    expected_mwh = preds["expected_constraint_mwh"]
    low_80 = preds["interval_80_lower_mwh"]
    high_80 = preds["interval_80_upper_mwh"]
    low_90 = preds["interval_90_lower_mwh"]
    high_90 = preds["interval_90_upper_mwh"]

    # Baseline predictions
    bl_preds = bundle.predict_baseline(test_df)
    p_bl = bl_preds["baseline_event_probability"]
    expected_mwh_bl = bl_preds["baseline_expected_mwh"]
    zero_preds = np.zeros_like(y_test)
    mean_preds = np.full_like(y_test, bundle.train_mean_mwh)

    # Classification metrics
    event_prevalence = float(np.mean(e_test))
    pr_auc = float(average_precision_score(e_test, p))
    roc_auc = float(roc_auc_score(e_test, p)) if len(np.unique(e_test)) > 1 else 0.5
    brier = float(brier_score_loss(e_test, p))
    pred_binary = (p >= 0.5).astype(int)
    prec_at_05 = float(precision_score(e_test, pred_binary, zero_division=0))
    rec_at_05 = float(recall_score(e_test, pred_binary, zero_division=0))

    # Calibration error
    ece, reliability_bins = expected_calibration_error(e_test, p, n_bins=10)

    # Baseline classification metrics
    bl_pr_auc = float(average_precision_score(e_test, p_bl))
    bl_brier = float(brier_score_loss(e_test, p_bl))

    # Volume error metrics
    model_mae = float(mean_absolute_error(y_test, expected_mwh))
    model_rmse = float(root_mean_squared_error(y_test, expected_mwh))

    zero_mae = float(mean_absolute_error(y_test, zero_preds))
    zero_rmse = float(root_mean_squared_error(y_test, zero_preds))

    train_mean_mae = float(mean_absolute_error(y_test, mean_preds))
    train_mean_rmse = float(root_mean_squared_error(y_test, mean_preds))

    cal_lag_mae = float(mean_absolute_error(y_test, expected_mwh_bl))
    cal_lag_rmse = float(root_mean_squared_error(y_test, expected_mwh_bl))

    # Relative improvement: positive means model reduced error compared to baseline
    improvement_vs_zero_pct = float((zero_mae - model_mae) / zero_mae * 100.0)
    improvement_vs_train_mean_pct = float((train_mean_mae - model_mae) / train_mean_mae * 100.0)
    improvement_vs_cal_lag_pct = float((cal_lag_mae - model_mae) / cal_lag_mae * 100.0)

    # Uncertainty interval coverage
    covered_80 = (y_test >= low_80) & (y_test <= high_80)
    cov_80_rate = float(np.mean(covered_80))
    width_80_mean = float(np.mean(high_80 - low_80))

    covered_90 = (y_test >= low_90) & (y_test <= high_90)
    cov_90_rate = float(np.mean(covered_90))
    width_90_mean = float(np.mean(high_90 - low_90))

    # Honest diagnosis of improvement
    beats_all_baselines = bool(model_mae < zero_mae and model_mae < cal_lag_mae)
    no_improvement = bool(model_mae >= cal_lag_mae or model_mae >= zero_mae)

    return {
        "test_intervals": n_test,
        "event_prevalence": round(event_prevalence, 4),
        "event_definition": f"constraint_mwh > {bundle.threshold_mwh}",
        "classification": {
            "occurrence_pr_auc": round(pr_auc, 4),
            "occurrence_roc_auc": round(roc_auc, 4),
            "brier_score": round(brier, 4),
            "expected_calibration_error": round(ece, 4),
            "precision_at_0_5": round(prec_at_05, 4),
            "recall_at_0_5": round(rec_at_05, 4),
            "baseline_calendar_lag_pr_auc": round(bl_pr_auc, 4),
            "baseline_calendar_lag_brier": round(bl_brier, 4),
            "reliability_bins": reliability_bins,
        },
        "volume_mwh": {
            "model_expected_mae_mwh": round(model_mae, 2),
            "model_expected_rmse_mwh": round(model_rmse, 2),
            "zero_baseline_mae_mwh": round(zero_mae, 2),
            "zero_baseline_rmse_mwh": round(zero_rmse, 2),
            "train_mean_baseline_mae_mwh": round(train_mean_mae, 2),
            "train_mean_baseline_rmse_mwh": round(train_mean_rmse, 2),
            "calendar_lag_baseline_mae_mwh": round(cal_lag_mae, 2),
            "calendar_lag_baseline_rmse_mwh": round(cal_lag_rmse, 2),
            "mae_reduction_vs_zero_pct": round(improvement_vs_zero_pct, 2),
            "mae_reduction_vs_train_mean_pct": round(improvement_vs_train_mean_pct, 2),
            "mae_reduction_vs_calendar_lag_pct": round(improvement_vs_cal_lag_pct, 2),
            "beats_all_baselines": beats_all_baselines,
            "no_improvement_flag": no_improvement,
        },
        "uncertainty_intervals": {
            "nominal_80_coverage": 0.80,
            "empirical_80_coverage": round(cov_80_rate, 4),
            "mean_80_interval_width_mwh": round(width_80_mean, 2),
            "nominal_90_coverage": 0.90,
            "empirical_90_coverage": round(cov_90_rate, 4),
            "mean_90_interval_width_mwh": round(width_90_mean, 2),
        },
    }

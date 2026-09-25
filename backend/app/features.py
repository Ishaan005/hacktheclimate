from __future__ import annotations

import numpy as np
import pandas as pd


def add_calendar_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out[timestamp_col])
    hour = ts.dt.hour + ts.dt.minute / 60.0
    dow = ts.dt.dayofweek
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    out["is_weekend"] = (dow >= 5).astype(int)
    return out


def add_historical_features(
    df: pd.DataFrame,
    cols: tuple[str, ...] = ("load_mw", "wind_onshore_mw", "sem_price_currency_per_mwh"),
) -> pd.DataFrame:
    """Features safe for a future forecast when built from rows strictly before prediction time.

    At 30-minute resolution: 2=1h, 4=2h, 48=24h, 336=7d.
    """
    out = df.sort_values("timestamp").copy()
    for col in cols:
        if col not in out:
            continue
        for lag in (2, 4, 48, 336):
            out[f"{col}_lag_{lag}"] = out[col].shift(lag)
        historical = out[col].shift(1)
        for window in (6, 12, 48):  # 3h, 6h, 24h
            out[f"{col}_rollmean_{window}"] = historical.rolling(window, min_periods=max(2, window // 3)).mean()
            out[f"{col}_rollstd_{window}"] = historical.rolling(window, min_periods=max(2, window // 3)).std()
    if "wind_onshore_mw" in out:
        out["wind_ramp_1h_mw"] = out["wind_onshore_mw"].shift(1) - out["wind_onshore_mw"].shift(3)
    if "load_mw" in out:
        out["load_ramp_1h_mw"] = out["load_mw"].shift(1) - out["load_mw"].shift(3)
    return out

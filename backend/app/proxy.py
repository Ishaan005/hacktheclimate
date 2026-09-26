from __future__ import annotations

import pandas as pd


def add_pressure_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """Add a transparent UI/demo proxy for renewable dispatch-down pressure.

    IMPORTANT: `pressure_proxy` is NOT a probability, NOT a curtailment label, and NOT a
    trained model. It remains a UI diagnostic even though real dispatch-down labels
    are now available separately.
    """
    out = df.copy()
    required = ["renewable_vre_share", "residual_load_mw", "sem_price_currency_per_mwh"]
    if any(c not in out for c in required):
        raise ValueError(f"Missing one of: {required}")

    vres = out["renewable_vre_share"].rank(pct=True)
    low_residual = 1 - out["residual_load_mw"].rank(pct=True)
    low_price = 1 - out["sem_price_currency_per_mwh"].rank(pct=True)
    out["pressure_proxy"] = 0.50 * vres + 0.20 * low_residual + 0.30 * low_price
    return out

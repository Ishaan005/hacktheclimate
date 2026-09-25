from __future__ import annotations

from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from .proxy import add_pressure_proxy

app = FastAPI(title="Team Blue — Hack the Climate API", version="0.1.0")
DATA = Path("data/processed/canonical_ie.csv")
LABELED_DATA = Path("data/processed/training_table_labeled_jan2026.csv")


def _json_records(df: pd.DataFrame, cols: list[str], limit: int) -> list[dict]:
    sample = df[cols].tail(max(1, min(limit, 336)))
    # The source data deliberately retains gaps; JSON must represent them as null.
    return sample.astype(object).where(pd.notna(sample), None).to_dict(orient="records")


@app.get("/health")
def health():
    return {"status": "ok", "canonical_data_exists": DATA.exists()}


@app.get("/v1/sample/pressure")
def sample_pressure(limit: int = 48):
    if not DATA.exists():
        raise HTTPException(404, "Run scripts/build_canonical.py first")
    df = pd.read_csv(DATA, parse_dates=["timestamp"])
    df = add_pressure_proxy(df)
    cols = [
        "timestamp",
        "load_mw",
        "wind_onshore_mw",
        "solar_mw",
        "renewable_vre_share",
        "residual_load_mw",
        "sem_price_currency_per_mwh",
        "pressure_proxy",
    ]
    return _json_records(df, cols, limit)


@app.get("/v1/sample/dispatch-down")
def sample_dispatch_down(limit: int = 96):
    if not LABELED_DATA.exists():
        raise HTTPException(404, "Build data/processed/training_table_labeled_jan2026.csv first")
    df = pd.read_csv(LABELED_DATA, parse_dates=["timestamp"])
    cols = [
        "timestamp", "dispatch_down_total_mwh", "constraint_mwh", "curtailment_mwh",
        "wind_dispatch_down_total_mwh", "solar_dispatch_down_total_mwh",
        "eirgrid_snsp_pct", "eirgrid_ie_demand_mw", "eirgrid_ie_wind_availability_mw",
        "eirgrid_ewic_ic_mw", "eirgrid_greenlink_ic_mw", "sem_price_currency_per_mwh",
    ]
    cols = [c for c in cols if c in df.columns]
    return _json_records(df, cols, limit)

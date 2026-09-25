from __future__ import annotations

import argparse
from pathlib import Path
import re
import pandas as pd
import numpy as np

GEN_REQUIRED = {"DateTime", "MapCode", "ActualGenerationOutput", "ProductionType"}
LOAD_REQUIRED = {"DateTime", "MapCode", "TotalLoadValue"}
PRICE_REQUIRED = {"DateTime", "MapCode", "Price[Currency/MWh]", "UpdateTime(UTC)"}


def require_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{name}: missing required columns: {sorted(missing)}")


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    aliases = {
        "wind_onshore": "wind_onshore_mw",
        "solar": "solar_mw",
        "fossil_gas": "fossil_gas_mw",
        "fossil_hard_coal": "fossil_hard_coal_mw",
        "fossil_oil": "fossil_oil_mw",
        "fossil_peat": "fossil_peat_mw",
        "hydro_pumped_storage": "hydro_pumped_storage_mw",
        "hydro_run_of_river_and_poundage": "hydro_run_of_river_mw",
        "other": "other_mw",
        "wind_offshore": "wind_offshore_mw",
    }
    return aliases.get(value, f"{value}_mw")


def build(generation_path: Path, load_path: Path, prices_path: Path) -> pd.DataFrame:
    gen = pd.read_csv(generation_path)
    load = pd.read_csv(load_path)
    prices = pd.read_csv(prices_path)
    require_columns(gen, GEN_REQUIRED, "generation")
    require_columns(load, LOAD_REQUIRED, "load")
    require_columns(prices, PRICE_REQUIRED, "prices")

    for df in (gen, load, prices):
        df["timestamp"] = pd.to_datetime(df["DateTime"], errors="raise")

    # Ireland-only sample. The organiser uses IE for generation/load and IE_SEM for price.
    gen_ie = gen.loc[gen["MapCode"].eq("IE")].copy()
    load_ie = load.loc[load["MapCode"].eq("IE")].copy()
    price_ie = prices.loc[prices["MapCode"].eq("IE_SEM")].copy()
    if gen_ie.empty or load_ie.empty or price_ie.empty:
        raise ValueError("Expected IE generation/load and IE_SEM prices in organiser samples.")

    # Duplicate source keys are aggregated explicitly instead of silently keeping one row.
    gen_ie = (
        gen_ie.groupby(["timestamp", "ProductionType"], as_index=False)["ActualGenerationOutput"]
        .mean()
    )
    load_ie = load_ie.groupby("timestamp", as_index=False)["TotalLoadValue"].mean()
    price_ie = price_ie.groupby("timestamp", as_index=False)["Price[Currency/MWh]"].mean()

    gen_wide = gen_ie.pivot(index="timestamp", columns="ProductionType", values="ActualGenerationOutput")
    gen_wide = gen_wide.rename(columns={c: slug(c) for c in gen_wide.columns})

    start = min(gen_ie["timestamp"].min(), load_ie["timestamp"].min(), price_ie["timestamp"].min())
    end = max(gen_ie["timestamp"].max(), load_ie["timestamp"].max(), price_ie["timestamp"].max())
    index = pd.date_range(start.floor("30min"), end.ceil("30min"), freq="30min", name="timestamp")

    out = gen_wide.reindex(index)
    out = out.join(load_ie.set_index("timestamp")["TotalLoadValue"].rename("load_mw"))

    # SEM sample is hourly. Repeat an hourly price into the two constituent half-hours.
    # This is NOT interpolation; it preserves the source's hourly period price.
    sem = price_ie.set_index("timestamp")["Price[Currency/MWh]"].sort_index()
    sem_30 = sem.reindex(index).ffill(limit=1)
    out = out.join(sem_30.rename("sem_price_currency_per_mwh"))

    # Ensure the two key VRE columns exist, but do not impute missing intervals.
    if "wind_onshore_mw" not in out:
        out["wind_onshore_mw"] = np.nan
    if "solar_mw" not in out:
        out["solar_mw"] = np.nan

    out["renewable_vre_mw"] = out["wind_onshore_mw"] + out["solar_mw"]
    out["renewable_vre_share"] = out["renewable_vre_mw"] / out["load_mw"]
    out["residual_load_mw"] = out["load_mw"] - out["renewable_vre_mw"]

    generation_cols = [c for c in out.columns if c.endswith("_mw") and c not in {"load_mw", "renewable_vre_mw", "residual_load_mw"}]
    out["known_generation_mw"] = out[generation_cols].sum(axis=1, min_count=1)

    # Quality flags. Do not silently fill missing source intervals.
    out["generation_complete"] = out[generation_cols].notna().all(axis=1)
    out["load_complete"] = out["load_mw"].notna()
    out["price_complete"] = out["sem_price_currency_per_mwh"].notna()

    return out.reset_index()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--generation", required=True, type=Path)
    p.add_argument("--load", required=True, type=Path)
    p.add_argument("--prices", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    df = build(args.generation, args.load, args.prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"wrote {len(df):,} rows -> {args.output}")
    print(df[["generation_complete", "load_complete", "price_complete"]].mean().rename("coverage"))


if __name__ == "__main__":
    main()

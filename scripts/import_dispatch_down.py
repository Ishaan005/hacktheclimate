from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

# Exact schema used by EirGrid/SONI's DD-HH annual workbooks.
OFFICIAL_DD_COLUMNS = {
    "UT_TYPE": "fuel",
    "JURISDICTION": "jurisdiction",
    "HH_TIMESTAMP": "local_timestamp",
    "GMT_OFFSET": "gmt_offset_hours",
    "Sum of AV_MWH": "available_energy_mwh",
    "Sum of AO_MWH": "actual_output_mwh",
    "Sum of HI_FRQ_MIN_GEN_MWH": "dd_curtailment_highfreq_mingen_mwh",
    "Sum of ROCOF_INERTIA_MWH": "dd_curtailment_rocof_inertia_mwh",
    "Sum of SNSP_MWH": "dd_curtailment_snsp_mwh",
    "Sum of TRANS_CONSTR_MWH": "dd_constraint_transmission_mwh",
    "Sum of TSO_TEST_MWH": "dd_constraint_tso_testing_mwh",
    "Sum of DD_MWH": "dispatch_down_total_mwh",
    "Sum of CURTAILMENTS_MWH": "curtailment_mwh",
    "Sum of CONSTRAINTS_MWH": "constraint_mwh",
    "Sum of OTHER_MWH": "other_reductions_mwh",
}


def norm(s: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _parse_official_timestamp(series: pd.Series) -> pd.Series:
    """Parse HH_TIMESTAMP from an official DD-HH workbook.

    EirGrid's notes define HH_TIMESTAMP as local calendar time with summer-time offset
    represented separately in GMT_OFFSET. Depending on the Excel reader, the values may
    already be datetimes or may still be Excel serial-day numbers.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    numeric = pd.to_numeric(series, errors="coerce")
    # Excel serial dates are around 40k-50k for modern years. Avoid treating arbitrary
    # strings or nanosecond timestamps as Excel serials.
    is_excel_serial = numeric.between(20000, 80000)
    if is_excel_serial.any():
        parsed.loc[is_excel_serial] = pd.to_datetime(
            numeric.loc[is_excel_serial], unit="D", origin="1899-12-30", errors="coerce"
        )
    remaining = ~is_excel_serial
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(series.loc[remaining], dayfirst=True, errors="coerce")
    return parsed


def normalize_official_dd_hh(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in OFFICIAL_DD_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Not an official DD-HH table; missing columns: {missing}")

    out = df[list(OFFICIAL_DD_COLUMNS)].rename(columns=OFFICIAL_DD_COLUMNS).copy()
    out["local_timestamp"] = _parse_official_timestamp(out["local_timestamp"])
    out["gmt_offset_hours"] = pd.to_numeric(out["gmt_offset_hours"], errors="coerce").fillna(0.0)
    out = out.loc[out["local_timestamp"].notna()].copy()

    # The workbook notes explicitly say: UTC = HH_TIMESTAMP - GMT_OFFSET hours.
    out["timestamp"] = out["local_timestamp"] - pd.to_timedelta(out["gmt_offset_hours"], unit="h")

    numeric_cols = [
        c for c in out.columns
        if c.endswith("_mwh") or c in {"gmt_offset_hours"}
    ]
    for c in numeric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    out["fuel"] = out["fuel"].astype(str).str.strip().str.lower()
    out["jurisdiction"] = out["jurisdiction"].astype(str).str.strip().str.upper()

    # Internal consistency checks from the workbook Notes sheet.
    out["dd_formula_error_mwh"] = (
        out["dispatch_down_total_mwh"]
        - out["constraint_mwh"]
        - out["curtailment_mwh"]
    )
    out["constraint_formula_error_mwh"] = (
        out["constraint_mwh"]
        - out["dd_constraint_transmission_mwh"]
        - out["dd_constraint_tso_testing_mwh"]
    )
    out["curtailment_formula_error_mwh"] = (
        out["curtailment_mwh"]
        - out["dd_curtailment_highfreq_mingen_mwh"]
        - out["dd_curtailment_rocof_inertia_mwh"]
        - out["dd_curtailment_snsp_mwh"]
    )
    return out.sort_values(["timestamp", "jurisdiction", "fuel"])



def normalize_sheet(df: pd.DataFrame, sheet_name: str = "") -> pd.DataFrame:
    """Backward-compatible normalizer for simple non-official DD tables used in tests/demos."""
    if set(OFFICIAL_DD_COLUMNS).issubset(df.columns):
        return normalize_official_dd_hh(df)

    def find_col(*needles: str) -> str | None:
        for c in df.columns:
            nc = norm(c)
            if all(norm(n) in nc for n in needles):
                return c
        return None

    ts_col = find_col("date", "time") or find_col("timestamp") or find_col("time")
    if ts_col is None:
        raise ValueError("Could not identify timestamp column")
    ts = pd.to_datetime(df[ts_col], dayfirst=True, errors="coerce")
    keep = ts.notna()
    d = df.loc[keep].copy()
    out = pd.DataFrame({"timestamp": ts.loc[keep]})
    out["fuel"] = (d[find_col("fuel")].astype(str).str.lower() if find_col("fuel") else ("solar" if "solar" in sheet_name.lower() else "wind"))
    out["jurisdiction"] = d[find_col("jurisdiction")].astype(str).str.upper() if find_col("jurisdiction") else "IE"

    def num(col):
        return pd.to_numeric(d[col], errors="coerce").fillna(0.0) if col else pd.Series(0.0, index=d.index)

    out["dd_curtailment_snsp_mwh"] = num(find_col("snsp"))
    out["dd_curtailment_rocof_inertia_mwh"] = num(find_col("rocof")) + num(find_col("inertia")) if not find_col("rocof", "inertia") else num(find_col("rocof", "inertia"))
    out["dd_curtailment_highfreq_mingen_mwh"] = num(find_col("high", "freq"))
    if out["dd_curtailment_highfreq_mingen_mwh"].eq(0).all():
        out["dd_curtailment_highfreq_mingen_mwh"] = num(find_col("min", "gen"))
    out["dd_constraint_transmission_mwh"] = num(find_col("transmission", "constraint"))
    out["dd_constraint_tso_testing_mwh"] = num(find_col("tso", "testing"))
    out["tso_testing_mwh"] = out["dd_constraint_tso_testing_mwh"]
    out["curtailment_mwh"] = out[["dd_curtailment_snsp_mwh","dd_curtailment_rocof_inertia_mwh","dd_curtailment_highfreq_mingen_mwh"]].sum(axis=1)
    out["constraint_mwh"] = out[["dd_constraint_transmission_mwh","dd_constraint_tso_testing_mwh"]].sum(axis=1)
    out["dispatch_down_total_mwh"] = out["curtailment_mwh"] + out["constraint_mwh"]
    return out

def load_one_workbook(path: Path) -> pd.DataFrame:
    # Official files use sheet name 'DD HH'; fall back to first sheet for resilience.
    xls = pd.ExcelFile(path)
    sheet = "DD HH" if "DD HH" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)
    out = normalize_official_dd_hh(df)
    out["source_file"] = path.name
    return out


def aggregate_ie(long: pd.DataFrame) -> pd.DataFrame:
    ie = long.loc[long["jurisdiction"].eq("IE")].copy()
    if ie.empty:
        raise ValueError("No IE rows found in dispatch-down data.")

    value_cols = [
        "available_energy_mwh",
        "actual_output_mwh",
        "dd_curtailment_highfreq_mingen_mwh",
        "dd_curtailment_rocof_inertia_mwh",
        "dd_curtailment_snsp_mwh",
        "dd_constraint_transmission_mwh",
        "dd_constraint_tso_testing_mwh",
        "dispatch_down_total_mwh",
        "curtailment_mwh",
        "constraint_mwh",
        "other_reductions_mwh",
    ]
    total = ie.groupby("timestamp", as_index=False)[value_cols].sum(min_count=1)

    for fuel in ("wind", "solar"):
        f = ie.loc[ie["fuel"].eq(fuel)].groupby("timestamp", as_index=False)[value_cols].sum(min_count=1)
        rename = {c: f"{fuel}_{c}" for c in value_cols}
        total = total.merge(f.rename(columns=rename), on="timestamp", how="left")

    total["dispatch_down_event"] = (total["dispatch_down_total_mwh"] > 0).astype(int)
    total["dispatch_down_gt_5_mwh"] = (total["dispatch_down_total_mwh"] > 5).astype(int)
    total["dispatch_down_gt_10_mwh"] = (total["dispatch_down_total_mwh"] > 10).astype(int)
    total["dispatch_down_total_mw_equiv"] = total["dispatch_down_total_mwh"] / 0.5
    total["constraint_mw_equiv"] = total["constraint_mwh"] / 0.5
    total["curtailment_mw_equiv"] = total["curtailment_mwh"] / 0.5
    return total.sort_values("timestamp")


def load_dispatch_down(paths: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    longs = [load_one_workbook(p) for p in paths]
    long = pd.concat(longs, ignore_index=True).sort_values(["timestamp", "jurisdiction", "fuel"])
    total = aggregate_ie(long)
    return long, total


def main() -> None:
    p = argparse.ArgumentParser(description="Normalize official EirGrid/SONI DD-HH workbooks.")
    p.add_argument("--input", required=True, type=Path, nargs="+", help="One or more DD-HH .xlsx files")
    p.add_argument("--output", type=Path, default=Path("data/processed/dispatch_down_labels_ie.csv"))
    p.add_argument("--long-output", type=Path, default=None, help="Optional IE/NI wind/solar long-form output")
    args = p.parse_args()

    long, total = load_dispatch_down(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    total.to_csv(args.output, index=False)
    if args.long_output:
        args.long_output.parent.mkdir(parents=True, exist_ok=True)
        long.to_csv(args.long_output, index=False)

    print(f"wrote {len(total):,} IE half-hours -> {args.output}")
    print(f"range: {total['timestamp'].min()} to {total['timestamp'].max()}")
    print(f"dispatch-down MWh: {total['dispatch_down_total_mwh'].sum():,.1f}")
    print(f"constraint MWh: {total['constraint_mwh'].sum():,.1f}")
    print(f"curtailment MWh: {total['curtailment_mwh'].sum():,.1f}")

    # Official formula consistency should be effectively exact apart from float noise.
    for c in ("dd_formula_error_mwh", "constraint_formula_error_mwh", "curtailment_formula_error_mwh"):
        max_err = long[c].abs().max()
        print(f"max |{c}|: {max_err:.6g}")


if __name__ == "__main__":
    main()

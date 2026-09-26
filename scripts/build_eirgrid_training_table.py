from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

if __package__:
    from .import_eirgrid_qtr_workbook import load_context
else:
    from import_eirgrid_qtr_workbook import load_context


def build(workbook: Path, labels_path: Path, year: int, first_month: int, last_month: int) -> pd.DataFrame:
    if not 1 <= first_month <= last_month <= 12:
        raise ValueError("Choose a valid inclusive month range.")

    context = pd.concat(
        [load_context(workbook, year, month) for month in range(first_month, last_month + 1)],
        ignore_index=True,
    ).sort_values("timestamp")
    labels = pd.read_csv(labels_path, parse_dates=["timestamp"])
    if context["timestamp"].duplicated().any() or labels["timestamp"].duplicated().any():
        raise ValueError("Context and label timestamps must each be unique.")

    out = context.merge(labels, on="timestamp", how="left", validate="one_to_one")
    if out["dispatch_down_total_mwh"].isna().any():
        missing = int(out["dispatch_down_total_mwh"].isna().sum())
        raise ValueError(f"{missing} system-context half-hours have no official DD label.")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Join the EirGrid system workbook to official DD labels.")
    p.add_argument("--input", required=True, type=Path, help="Quarter-hourly EirGrid system workbook")
    p.add_argument("--labels", required=True, type=Path, help="Combined official IE DD label CSV")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--first-month", type=int, default=1)
    p.add_argument("--last-month", type=int, default=8)
    p.add_argument("--output", type=Path, default=Path("data/processed/training_table_eirgrid_2026_jan_aug.csv"))
    args = p.parse_args()

    out = build(args.input, args.labels, args.year, args.first_month, args.last_month)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"wrote {len(out):,} labeled EirGrid half-hours -> {args.output}")
    print(f"UTC range: {out['timestamp'].min()} to {out['timestamp'].max()}")


if __name__ == "__main__":
    main()

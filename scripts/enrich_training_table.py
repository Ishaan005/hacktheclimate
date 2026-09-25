from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def merge(canonical: Path, context: Path | None, labels: Path | None) -> pd.DataFrame:
    base = pd.read_csv(canonical)
    base["timestamp"] = pd.to_datetime(base["timestamp"])
    out = base
    for p in (context, labels):
        if p is None:
            continue
        df = pd.read_csv(p)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # Avoid duplicate column names except timestamp.
        collisions = (set(out.columns) & set(df.columns)) - {"timestamp"}
        if collisions:
            df = df.drop(columns=sorted(collisions))
        out = out.merge(df, on="timestamp", how="left")
    return out.sort_values("timestamp")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--canonical", type=Path, required=True)
    p.add_argument("--context", type=Path)
    p.add_argument("--labels", type=Path)
    p.add_argument("--output", type=Path, default=Path("data/processed/training_table.csv"))
    args = p.parse_args()
    out = merge(args.canonical, args.context, args.labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"wrote {len(out):,} rows -> {args.output}")
    coverage_cols = [c for c in out.columns if c.startswith("interconnector_") or c in {"snsp_pct", "dispatch_down_total_mwh", "constraint_mwh", "curtailment_mwh"}]
    if coverage_cols:
        print(out[coverage_cols].notna().mean().rename("coverage").sort_values().to_string())


if __name__ == "__main__":
    main()

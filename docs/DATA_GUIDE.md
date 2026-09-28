# Data guide

The processed data and trained artifacts are included so a teammate can clone the repo and run the API without the source CSVs or Excel workbooks. Run commands from the repository root with the Python 3.11 environment in the [README](../README.md).

## Choose the right file

| File | Role |
| --- | --- |
| [`canonical_ie.csv`](../data/processed/canonical_ie.csv) | January 2026 organiser generation, load, and price data on 1,488 Irish half-hours; input to the pressure sample route |
| [`eirgrid_context_jan2026_from_workbook.csv`](../data/processed/eirgrid_context_jan2026_from_workbook.csv) | January system measurements from the versioned quarter-hourly EirGrid workbook, aggregated to half-hours |
| [`dispatch_down_labels_ie_2021_2026.csv`](../data/processed/dispatch_down_labels_ie_2021_2026.csv) | Official dispatch-down, constraint, and curtailment targets for 99,310 Irish half-hours through August 2026 |
| [`training_table_labeled_jan2026.csv`](../data/processed/training_table_labeled_jan2026.csv) | January canonical data, EirGrid context, and real labels joined by timestamp; input to baseline training and the dispatch-down sample route |
| [`training_table_eirgrid_2026_jan_aug.csv`](../data/processed/training_table_eirgrid_2026_jan_aug.csv) | 11,662 EirGrid system-context half-hours joined to official labels on UTC timestamps; use for multi-month model experiments, without organiser prices |
| [`gfs_daily_2026_jan_aug.csv`](../data/processed/gfs_daily_2026_jan_aug.csv) | 243 daily 00Z NOAA GFS vintages at five Irish points, with 100 m wind, temperature, radiation, 06Z decision time and checked source availability; see the [source manifests](GFS_CONSTRAINT_TRAINING.md) |
| [`gfs_constraint_training_2026_jan_aug.csv`](../data/processed/gfs_constraint_training_2026_jan_aug.csv) | 11,649 unique half-hour constraint targets joined to forecast-safe GFS and calendar features; excludes measured grid state as predictors |
| [`training_table_context_jan2026.csv`](../data/processed/training_table_context_jan2026.csv) | Earlier context-only join; use the labeled table for supervised work |
| `dd_ie_2021.csv` … `dd_ie_2025.csv`, `dispatch_down_labels_ie_2026.csv` | Annual label extracts retained for inspection; the combined label file is the default |
| [`artifacts/real_baseline/`](../artifacts/real_baseline/) | Four January model files and [`metrics.json`](../artifacts/real_baseline/metrics.json); smoke-test artifacts, not a validated deployment |
| [`artifacts/gfs_constraint/`](../artifacts/gfs_constraint/) | National 0.5–24 hour weather model, calendar baseline, monthly backtest metrics, held-out predictions and a final candidate calibrated on August; research artifact, not a validated operating forecast |

The original organiser CSVs and EirGrid XLSX workbooks are **not tracked** in this repo. In the original local workspace they sit one directory above it. A fresh clone can use its included processed files immediately; rebuilding requires a copy of those source files. Keep source files under `data/raw/` or another untracked location and do not commit credentials or private exports.

## Rebuild from the original files

If the original workspace layout is available, set `SOURCE_DIR=..`. Otherwise point it at a directory with `generation.csv`, `load.csv`, `prices.csv`, `System-Data-Qtr-Hourly-2026-V8.xlsx`, and the `Dispatch Down Half-Hourly Data Reports` subfolder. The Bash commands below use workbook names matching the files inspected in this workspace. On PowerShell, pass the same paths as arguments using its own variable and line-continuation syntax.

```bash
SOURCE_DIR=..
python scripts/build_canonical.py \
  --generation "$SOURCE_DIR/generation.csv" \
  --load "$SOURCE_DIR/load.csv" \
  --prices "$SOURCE_DIR/prices.csv" \
  --output data/processed/canonical_ie.csv

python scripts/import_eirgrid_qtr_workbook.py \
  --input "$SOURCE_DIR/System-Data-Qtr-Hourly-2026-V8.xlsx" \
  --year 2026 --month 1 \
  --output data/processed/eirgrid_context_jan2026_from_workbook.csv

python scripts/import_dispatch_down.py --input \
  "$SOURCE_DIR/Dispatch Down Half-Hourly Data Reports/DD-HH-2021.xlsx" \
  "$SOURCE_DIR/Dispatch Down Half-Hourly Data Reports/DD-HH-2022.xlsx" \
  "$SOURCE_DIR/Dispatch Down Half-Hourly Data Reports/DD-HH-2023.xlsx" \
  "$SOURCE_DIR/Dispatch Down Half-Hourly Data Reports/DD-HH-2024.xlsx" \
  "$SOURCE_DIR/Dispatch Down Half-Hourly Data Reports/DD-HH-2025-v10.xlsx" \
  "$SOURCE_DIR/Dispatch Down Half-Hourly Data Reports/DD-HH-2026-V9.xlsx" \
  --output data/processed/dispatch_down_labels_ie_2021_2026.csv

python scripts/enrich_training_table.py \
  --canonical data/processed/canonical_ie.csv \
  --context data/processed/eirgrid_context_jan2026_from_workbook.csv \
  --labels data/processed/dispatch_down_labels_ie_2021_2026.csv \
  --output data/processed/training_table_labeled_jan2026.csv

python scripts/build_eirgrid_training_table.py \
  --input "$SOURCE_DIR/System-Data-Qtr-Hourly-2026-V8.xlsx" \
  --labels data/processed/dispatch_down_labels_ie_2021_2026.csv \
  --output data/processed/training_table_eirgrid_2026_jan_aug.csv
```

These commands were verified against the supplied sources: rebuilt tables match the included values and coverage. CSV byte formatting can differ between pandas versions. Both EirGrid importers put timestamps on a UTC half-hour grid: the system workbook uses Irish local clock time and the DD importer uses its explicit `GMT_OFFSET`. The DD importer uses the official DD total; it does not infer labels from availability gaps. See the [label profile](DD_LABEL_PROFILE.md) for target semantics.

## Optional live-data route

`scripts/fetch_eirgrid_context.py` retrieves Smart Grid Dashboard data and writes its raw JSON responses under `data/raw/eirgrid/`. It is a fallback for exploration, not the versioned workbook used in the January baseline. Its columns and coverage differ from the workbook; inspect the output before joining it to training data.

```bash
python scripts/fetch_eirgrid_context.py --year 2026 --month 1 \
  --output data/raw/eirgrid/context_jan2026.csv
```

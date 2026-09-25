# Hack the Climate — Team Blue data/model starter

Pre-hackathon scaffold for the Ireland dispatch-down challenge.

## What this repo does

- Ingests the organiser sample files (`generation.csv`, `load.csv`, `prices.csv`).
- Normalises the Ireland data to a 30-minute canonical table without silently imputing missing values.
- Adds data-quality flags and derived renewable-pressure features.
- Separates **forecast-safe** lagged features from contemporaneous **nowcast/diagnostic** features to reduce leakage risk.
- Provides a deliberately labelled **pressure proxy** for UI development only. It is **not** a curtailment probability or a trained dispatch-down model.
- Ingests the official EirGrid/SONI DD-HH workbooks and builds real half-hourly dispatch-down / constraint / curtailment targets.
- Includes a small FastAPI service and tests.

## Important modelling rule

The supplied generation and load files contain **actual** values. Do not feed same-period actual generation/load into a model marketed as a day-ahead forecast. For forecasting, use their historical lags plus future-known/forecast inputs (for example weather, wind/load forecasts, calendar variables, and confirmed day-ahead prices).

## Quick start

From the repository root, with Python 3.11:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The included processed CSVs and baseline artifacts are sufficient to run the API now. Open `http://127.0.0.1:8000/docs` for the interactive API, or check `http://127.0.0.1:8000/health`.

The original organiser CSVs and EirGrid workbooks are not in `data/raw/`. In this local workspace they are one directory above the repo. To rebuild the canonical table here:

```bash
python scripts/build_canonical.py \
  --generation ../generation.csv \
  --load ../load.csv \
  --prices ../prices.csv \
  --output data/processed/canonical_ie.csv
```

## EirGrid enrichment

### Preferred path: official quarter-hourly workbook

The current EirGrid workbook supplied for the hackathon is a stronger source than the sample CSVs for system context. Import January 2026 and aggregate its 15-minute average SCADA values to the canonical 30-minute grid:

```bash
python scripts/import_eirgrid_qtr_workbook.py \
  --input /path/to/System-Data-Qtr-Hourly-2026-V8.xlsx \
  --year 2026 --month 1 \
  --output data/processed/eirgrid_context_jan2026_from_workbook.csv
```

This retains demand/generation, wind and solar availability/output, EWIC, Greenlink, Moyle, inter-jurisdictional flow, SNSP and all-island oversupply. It also creates an explicitly named `eirgrid_ie_vre_availability_gap_proxy_mw` diagnostic. **That proxy is not a dispatch-down label.**

The repository already includes the resulting January context and a merged organiser+EirGrid table:

- `data/processed/eirgrid_context_jan2026_from_workbook.csv`
- `data/processed/training_table_context_jan2026.csv`

### API fallback

The Smart Grid Dashboard fetcher is retained as an optional live-data path:

```bash
python scripts/fetch_eirgrid_context.py --year 2026 --month 1 \
  --output data/processed/eirgrid_context_jan2026.csv
```

### Real dispatch-down labels integrated

The official 2021–2026 DD-HH workbooks are now supported directly. The importer handles EirGrid's Excel timestamp + GMT-offset convention and uses the workbook's explicit DD totals rather than availability-gap proxies:

```bash
python scripts/import_dispatch_down.py \
  --input /path/to/DD-HH-2021.xlsx /path/to/DD-HH-2022.xlsx /path/to/DD-HH-2023.xlsx \
          /path/to/DD-HH-2024.xlsx /path/to/DD-HH-2025.xlsx /path/to/DD-HH-2026.xlsx \
  --output data/processed/dispatch_down_labels_ie_2021_2026.csv
```

The repo includes:

- `data/processed/dispatch_down_labels_ie_2021_2026.csv` — 99,310 IE half-hours
- `data/processed/training_table_labeled_jan2026.csv` — all 1,488 organiser January half-hours joined to real labels + EirGrid context
- `artifacts/real_baseline/metrics.json` — chronological smoke-test metrics

Train the real-label hackathon baseline with:

```bash
python scripts/train_real_baseline.py
```

See `docs/EIRGRID_UPLOADED_WORKBOOKS.md` for what is actually present in the two EirGrid workbooks inspected before the hackathon, and `docs/EIRGRID_SOURCES.md` for source/leakage notes.


See `docs/DD_LABEL_PROFILE.md` and `docs/REAL_BASELINE.md` for label semantics, coverage and modelling caveats.

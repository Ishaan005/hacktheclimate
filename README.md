# Hack the Climate — Team Blue

Data and modelling starter for the Ireland renewable dispatch-down challenge. The repository includes a small FastAPI service, data-processing scripts, an optimisation module, tests, processed datasets, and trained January 2026 baseline artifacts.

## Start here

Use Python 3.11. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version  # should report Python 3.11
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

On Windows PowerShell, create the environment with `py -3.11 -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`; then run the same `python` commands. Open [the API documentation](http://127.0.0.1:8000/docs) after starting the server. The processed CSVs needed for the API and the model artifacts are already in the repository. Original source workbooks are optional and are not required to run the API.

The API currently provides:

| Route | What it returns |
| --- | --- |
| `GET /health` | Service status and canonical-data presence |
| `GET /v1/sample/pressure?limit=48` | Historical rows with a **UI-only pressure proxy** |
| `GET /v1/sample/dispatch-down?limit=96` | Historical January rows with official dispatch-down labels |

Sample routes return up to 336 rows. Missing source values appear as JSON `null`. The API does **not** yet serve model predictions or an optimiser schedule.

## What is ready

- `data/processed/canonical_ie.csv`: 1,488 Irish half-hours in January 2026, joined from the organiser's generation, load, and price samples.
- `data/processed/dispatch_down_labels_ie_2021_2026.csv`: 99,310 Irish half-hours with official wind/solar dispatch-down labels through August 2026.
- `data/processed/training_table_labeled_jan2026.csv`: all 1,488 January organiser half-hours joined to EirGrid system context and real labels.
- `data/processed/training_table_eirgrid_2026_jan_aug.csv`: 11,662 EirGrid system half-hours joined to official labels through August, with timestamps aligned to UTC. It has no organiser price field outside January.
- `artifacts/real_baseline/`: a same-period nowcast and a 1-hour-ahead baseline trained on January, plus smoke-test metrics.

The current January holdout is **not** a reliable performance claim. A credible forecast still needs rolling multi-month validation and point-in-time forecast inputs such as weather. Same-period actual demand, generation, and grid state are valid for a nowcast, but must not be presented as day-ahead forecast inputs. The pressure proxy is not a probability or a dispatch-down label.

## Find your way around

| Path | Purpose |
| --- | --- |
| [`backend/app/`](backend/app/) | FastAPI routes, feature helpers, baseline model functions, and flexible-load optimiser |
| [`scripts/`](scripts/) | Import, merge, live-data fallback, and baseline-training commands |
| [`data/processed/`](data/processed/) | Included data products; see the [data guide](docs/DATA_GUIDE.md) before choosing a file |
| [`artifacts/real_baseline/`](artifacts/real_baseline/) | Trained smoke-test models and metrics |
| [`config/data_contract.yaml`](config/data_contract.yaml) | Canonical fields, targets, and feature-use boundaries |
| [`tests/`](tests/) | Pipeline and optimiser checks |
| [`docs/`](docs/) | [Documentation index](docs/README.md), source notes, profiles, and model caveats |

For work on the repo, read [CONTRIBUTING.md](CONTRIBUTING.md) and the [verified project status](docs/PROJECT_STATUS.md). To rebuild data from the original CSVs and workbooks, follow the [data guide](docs/DATA_GUIDE.md); those source files are not tracked here. To retrain the January baseline without overwriting the included artifacts:

```bash
python scripts/train_real_baseline.py --output-dir .cache/baseline-check
```

The optional Smart Grid Dashboard API fetcher is in `scripts/fetch_eirgrid_context.py`. Its output is separate from the preferred versioned EirGrid workbook import and should be checked for coverage before use.

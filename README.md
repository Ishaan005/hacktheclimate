# Hack the Climate — Team Blue

Data and modelling starter for the Ireland renewable dispatch-down challenge. The repository includes a FastAPI service, data-processing scripts, an optimisation module, tests, processed datasets, and trained January 2026 baseline artifacts.

## Requirements

| Tool | Version | Notes |
| --- | --- | --- |
| **Python** | Must be **3.11** | Required for the API, scripts, and tests. CI uses 3.11. |
| **Node.js** | Supported **22.x** release | Only if you work on the React app in `frontend/`; the current Vite, Vitest and jsdom dependencies require a recent Node runtime. |
| **npm** | Min **9+** (bundled with Node) | Comes with Node; used for `frontend/` install and build. |

You do **not** need Node to run the API, run tests, or use `/docs`. Install Node only when developing or building the UI.

## Running the application

Use Python 3.11. From the repository root:

## To run the backend + frontend
```bash
# From the repository root
python3.11 -m venv .venv
source .venv/bin/activate
python --version  # should report Python 3.11
python -m pip install -r requirements.txt
python -m pytest -q

cd frontend
npm install --include=dev
npm run build
cd ..

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## To run only the frontend
```bash
cd frontend
npm install
npm run dev
```

On Windows PowerShell, create the environment with `py -3.11 -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`; then run the same `python` commands. Open [the API documentation](http://127.0.0.1:8000/docs) after starting the server. The processed CSVs needed for the API and the model artifacts are already in the repository. Original source workbooks are optional and are not required to run the API.

The API currently provides:

| Route | What it returns |
| --- | --- |
| `GET /health` | Service status and canonical-data presence |
| `GET /v1/sample/pressure?limit=48` | Historical rows with a **UI-only pressure proxy** |
| `GET /v1/sample/dispatch-down?limit=96` | Historical January rows with official dispatch-down labels |
| `POST /v1/demo/absorption` | Retrospective January 1-hour model estimates passed to the flexible-load optimiser |
| `GET /v1/network/forecast` | Input-gated 48 half-hour TYTFS planning scenarios; requires a re-imported local case, reviewed generator crosswalk and timestamped upstream forecasts |
| `GET /v1/operator/view` | The same 48 future scenarios plus conservative safety checks, controlled action re-solves and explicit recommendation/data gaps |

Sample routes return up to 336 rows. Missing source values appear as JSON `null`. To try the model-to-optimiser route while the server is running:

```bash
curl -sS http://127.0.0.1:8000/v1/demo/absorption \
  -H 'Content-Type: application/json' \
  -d '{"start_target":"2026-01-24T00:00:00Z","intervals":4,"assets":[{"name":"flexible_load","max_power_mw":10,"energy_required_mwh":8,"available":[true,false,true,true]}]}'
```

`start_target` is a UTC half-hour in the **24–31 January 2026** held-out window; `intervals` is 1–48 and each asset needs one availability flag per interval. The route returns model probabilities, expected and observed dispatch-down MWh, and a power schedule. It replays historical inputs from one hour before each target; it is **not a live or day-ahead forecast**. Treating all predicted dispatch-down as locally absorbable is an unvalidated upper bound, and scheduled energy is not measured avoided dispatch-down.

The network route returns 503 until its local source case, reviewed crosswalk and 48 timestamped upstream rows are provided. See the [network forecast architecture](docs/NETWORK_FORECAST_ARCHITECTURE.md) for the input contract and planning-case limits. Its national probability and MWh values come from the supplied upstream rows; this route does not train or run a day-ahead national model.

The operator route uses those inputs and, optionally, a reviewed action catalog. It will not recommend an action while voltage, inertia, RoCoF or other required checks remain unknown. See [safety and action screening](docs/NETWORK_SAFETY_ACTIONS.md) for the catalog format and the distinction between modeled capture and validated avoided constraint MWh.

The [operator UI](frontend/README.md) calls this route by default and displays missing-input states. Set `VITE_API_MODE=fixture` only when deliberately viewing its offline planning-case fixture.

## What is ready

- `data/processed/canonical_ie.csv`: 1,488 Irish half-hours in January 2026, joined from the organiser's generation, load, and price samples.
- `data/processed/dispatch_down_labels_ie_2021_2026.csv`: 99,310 Irish half-hours with official wind/solar dispatch-down labels through August 2026.
- `data/processed/training_table_labeled_jan2026.csv`: all 1,488 January organiser half-hours joined to EirGrid system context and real labels.
- `data/processed/training_table_eirgrid_2026_jan_aug.csv`: 11,662 EirGrid system half-hours joined to official labels through August, with timestamps aligned to UTC. It has no organiser price field outside January.
- `artifacts/real_baseline/`: a same-period nowcast and a 1-hour-ahead baseline trained on January, plus smoke-test metrics.
- `artifacts/rolling_1h/metrics.json`: expanding-window April–August backtest of the 1-hour operational baseline, with per-fold prevalence and error baselines.

The January holdout alone is **not** a reliable performance claim. Multi-month validation is now included, but a credible day-ahead forecast still needs point-in-time forecast inputs such as weather. Publication latency for the measured 1-hour inputs has not been established. Same-period actual demand, generation, and grid state are valid for a nowcast, but must not be presented as day-ahead forecast inputs. The pressure proxy is not a probability or a dispatch-down label.

## Find your way around

| Path | Purpose |
| --- | --- |
| [`backend/app/`](backend/app/) | FastAPI routes, feature helpers, baseline model functions, and flexible-load optimiser |
| [`scripts/`](scripts/) | Import, merge, live-data fallback, and baseline-training commands |
| [`data/processed/`](data/processed/) | Included data products; see the [data guide](docs/DATA_GUIDE.md) before choosing a file |
| [`artifacts/real_baseline/`](artifacts/real_baseline/) | Trained smoke-test models and metrics |
| [`artifacts/rolling_1h/`](artifacts/rolling_1h/) | Monthly operational backtest results |
| [`config/data_contract.yaml`](config/data_contract.yaml) | Canonical fields, targets, and feature-use boundaries |
| [`tests/`](tests/) | Pipeline and optimiser checks |
| [`docs/`](docs/) | [Documentation index](docs/README.md), source notes, profiles, and model caveats |

For work on the repo, read [CONTRIBUTING.md](CONTRIBUTING.md) and the [verified project status](docs/PROJECT_STATUS.md). To rebuild data from the original CSVs and workbooks, follow the [data guide](docs/DATA_GUIDE.md); those source files are not tracked here. To retrain the January baseline without overwriting the included artifacts:

```bash
python scripts/train_real_baseline.py --output-dir .cache/baseline-check
python scripts/backtest_1h_operational.py --output .cache/rolling-check.json
```

The optional Smart Grid Dashboard API fetcher is in `scripts/fetch_eirgrid_context.py`. Its output is separate from the preferred versioned EirGrid workbook import and should be checked for coverage before use.

Pull requests and pushes run the same dependency and test checks in [GitHub Actions](.github/workflows/tests.yml).

For hackathon-day hosting, use the [Azure handoff](docs/AZURE_HANDOFF.md). It includes a small local container and a preview-first Container Apps command for use **after** the team receives access. No Azure resource or paid weather service is needed to develop or run the API locally.

The [Microsoft weather options](docs/WEATHER_OPTIONS.md) compare Azure Maps' hourly feed with Aurora 1.5 and record the data, cost, and retention questions to resolve when access arrives.

The [archived GFS constraint model](docs/GFS_CONSTRAINT_TRAINING.md) trains and backtests a national 0.5–24 hour forecast from source-checked NOAA weather vintages. Its August volume result does not beat the zero-MWh baseline; use the report's scope and confidence limits when showing it.
The [Microsoft weather options](docs/WEATHER_OPTIONS.md) compare Azure Maps' hourly feed with Aurora 1.5. A separate [audit of local May Aurora forecasts and Irish turbine coordinates](docs/AURORA_TURBINE_DATA_AUDIT.md) records their actual fields, coverage, and remaining source and timing checks.

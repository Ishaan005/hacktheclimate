# Hack the Climate — Team Blue

Ireland renewable dispatch-down prototype: a FastAPI service, operator UI, planning-network scenarios, and research forecast models. The included processed data and model artifacts let you run the local app without the original workbooks.

## Run locally

Use Python 3.11 for the API. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q

cd frontend
npm install --include=dev
npm run build
cd ..

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

On Windows, create the environment with `py -3.11 -m venv .venv` and activate `.venv\Scripts\Activate.ps1`. Open [the API docs](http://127.0.0.1:8000/docs) after starting the server.

For the UI, use a supported Node 22 release in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The UI calls `/v1/operator/view` by default. Without its reviewed network inputs, it shows unavailable states. For layout work, use `VITE_API_MODE=fixture npm run dev`. See the [UI guide](frontend/README.md) for tests and the fixture boundary.

## API paths

| Route | Purpose |
| --- | --- |
| `GET /health` | Basic service and canonical-data check |
| `GET /v1/sample/pressure` | Historical January organiser data and a UI-only pressure proxy |
| `GET /v1/sample/dispatch-down` | Historical January rows with official dispatch-down labels |
| `POST /v1/demo/absorption` | Retrospective January model-to-optimiser replay |
| `GET /v1/forecast/constraint` | Future intervals from the latest checked experimental GFS forecast; 503 when unavailable or expired |
| `GET /v1/network/forecast` | Input-gated planning-network scenarios |
| `GET /v1/operator/view` | Network scenarios, conservative safety checks and action gaps |

The January replay uses measured historical inputs and does not establish live forecasting or avoided-energy impact. The GFS model is a national constraint forecast; its August expected-MWh error did **not** beat a zero forecast. Network routes require a re-imported TYTFS case, reviewed generator crosswalk and current upstream forecasts. They do not infer a safe action from the GFS result alone.

Smoke-test the retrospective model-to-optimiser route with the API running:

```bash
curl -sS http://127.0.0.1:8000/v1/demo/absorption \
  -H 'Content-Type: application/json' \
  -d '{"start_target":"2026-01-24T00:00:00Z","intervals":4,"assets":[{"name":"flexible_load","max_power_mw":10,"energy_required_mwh":8,"available":[true,false,true,true]}]}'
```

## Work with the data and models

- [Data guide](docs/DATA_GUIDE.md): choose included files and rebuild them from the original workbooks.
- [GFS training report](docs/GFS_CONSTRAINT_TRAINING.md): weather vintages, forecast-safe features, backtests and model limits.
- [GFS inference runbook](docs/GFS_INFERENCE.md): checked daily job, versioned output and API serving.
- [Network forecast architecture](docs/NETWORK_FORECAST_ARCHITECTURE.md) and [safety checks](docs/NETWORK_SAFETY_ACTIONS.md): required inputs and operator boundaries.
- [UI data handoff](docs/ui-handoff/README.md): response fixtures, TypeScript types, units and evaluation outputs.
- [Documentation index](docs/README.md): source audits, historical baselines, network case and deployment guides.

Original organiser CSVs and EirGrid workbooks are outside Git. Processed datasets and historical model artifacts are retained for reproducibility. Run the GFS inference job after 06:00 UTC to create a current forecast; a clone has no live forecast snapshot until that job succeeds. Pull requests and pushes run the Python checks in [GitHub Actions](.github/workflows/tests.yml). For a local container and later Azure access, use the [Azure handoff](docs/AZURE_HANDOFF.md).

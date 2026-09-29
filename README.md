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
| `POST /v1/operator/evaluate` | Evaluate a supplied decision case, 48 forecast conditions and action set against the local planning case |
| `POST /v1/decision/preview` | Read-only case evidence, baseline, policy and missing-data preview |
| `GET /v1/decision/scenarios` | Locked T1–T4, H1–H4 and SNSP intake catalogue from issue #47 |

The January replay uses measured historical inputs and does not establish live forecasting or avoided-energy impact. The GFS model is a national constraint forecast; its August expected-MWh error did **not** beat a zero forecast. Network routes require a re-imported TYTFS case, reviewed generator crosswalk and current upstream forecasts. They do not infer a safe action from the GFS result alone.

Smoke-test the retrospective model-to-optimiser route with the API running:

```bash
curl -sS http://127.0.0.1:8000/v1/demo/absorption \
  -H 'Content-Type: application/json' \
  -d '{"start_target":"2026-01-24T00:00:00Z","intervals":4,"assets":[{"name":"flexible_load","max_power_mw":10,"energy_required_mwh":8,"available":[true,false,true,true]}]}'
```

To inspect the complete operator evaluation on the local TYTFS case, run the
clearly synthetic planning example:

```bash
.venv/bin/python -m scripts.run_operator_evaluation --example \
  --output data/raw/network_case/operator_example_output.json
```

The command also writes a request JSON beside the output. Edit that request to
use sourced case conditions and actions, then rerun with `--request PATH --output
PATH`. The checked-in [example request](examples/operator_evaluation/operator_example_output.request.json)
and [example output](examples/operator_evaluation/operator_example_output.json)
show the complete synthetic run. See [operator evaluation](docs/OPERATOR_EVALUATION.md)
for the input contract and evidence gates.

## Work with the data and models

- [Data guide](docs/DATA_GUIDE.md): choose included files and rebuild them from the original workbooks.
- [GFS training report](docs/GFS_CONSTRAINT_TRAINING.md): weather vintages, forecast-safe features, backtests and model limits.
- [GFS model readiness](docs/GFS_MODEL_READINESS.md): frozen forward path, curtailment experiment and explicit promotion gates.
- [GFS inference runbook](docs/GFS_INFERENCE.md): checked daily job, versioned output and API serving.
- [Network forecast architecture](docs/NETWORK_FORECAST_ARCHITECTURE.md) and [safety checks](docs/NETWORK_SAFETY_ACTIONS.md): required inputs and operator boundaries.
- [UI data handoff](docs/ui-handoff/README.md): response fixtures, TypeScript types, units and evaluation outputs.
- [Documentation index](docs/README.md): source audits, historical baselines, network case and deployment guides.

Original organiser CSVs and EirGrid workbooks are outside Git. Processed datasets and historical model artifacts are retained for reproducibility. Run the GFS inference job after 06:00 UTC to create a current forecast; a clone has no live forecast snapshot until that job succeeds. Pull requests and pushes run the Python checks in [GitHub Actions](.github/workflows/tests.yml). For a local container and later Azure access, use the [Azure handoff](docs/AZURE_HANDOFF.md).

## Chat assistant (Azure OpenAI + LangGraph)

`POST /v1/chat` answers questions by calling model-backed tools through LangGraph. It can query the January dispatch-down replay, the January–August constraint replay, the latest checked experimental GFS national constraint forecast, and the input-gated TYTFS planning-network scenario. Setup:

```bash
python -m pip install -r requirements-chat.txt
az login --tenant 6c51c659-9d52-41af-81f7-dde16380e813
az account set --subscription eb517801-6c35-40b5-8651-3fea5cc570b0
scripts/fetch_azure_openai_env.sh 12   # writes the git-ignored .env from Key Vault
```

A plain `az login` signs in to your personal directory and reports "No subscriptions found". Use the hackathon tenant above. If it is missing from Portal settings → Directories + subscriptions, accept the organiser invitation or ask to be added to `grp-hack-team12`.

To see the chat assistant's LangGraph (no Azure credentials needed):

```bash
ln -sf ../../bin/graph .venv/bin/graph   # once, so `graph` works whenever the venv is active
graph            # print it in the terminal
graph --view     # open an interactive diagram in your browser
graph --md       # regenerate docs/chat_graph.md after changing backend/app/chat/graph.py
graph --png      # write docs/chat_graph.png (needs internet)
```

Without the shortcut, use `bin/graph` or `python -m scripts.draw_chat_graph`.

To open a shell on the team 12 VM after signing in:

```bash
az extension add --name ssh   # once
az ssh vm -n vm-hack-team12 -g rg-hack-team12-swc
```

### Test the chat assistant

Start the API (see [Run locally](#run-locally)), then check that Azure OpenAI credentials are set:

```bash
curl -sS http://127.0.0.1:8000/v1/chat/status
```

`"configured": true` means the chat route is ready. If it is `false`, set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env` and restart the API.

Ask a question. This runs the full LangGraph flow: `load_actions -> agent -> (tools -> agent)* -> select_action`.

```bash
curl -sS http://127.0.0.1:8000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "What is the dispatch-down risk at this time, and what should I do?", "selected_target": "2026-01-24T01:00"}'
```

The reply looks like:

```json
{"thread_id": "3f2c...", "reply": "Historical replay: ... A location-specific action needs reviewed network and safety inputs.", "tools_used": ["get_dispatch_down_forecast"], "model": "gpt-4.1"}
```

To continue the same conversation, send the returned `thread_id` back:

```bash
curl -sS http://127.0.0.1:8000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Why that action?", "thread_id": "PASTE_THREAD_ID_HERE"}'
```

Request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `message` | Yes | The operator's question (1 to 4000 characters) |
| `thread_id` | No | Continues an earlier conversation; omit it to start a new one |
| `selected_target` | No | The UTC time selected in the UI, so "this time" refers to it |

The UI's situation box uses the same route. With the API and `npm run dev` running, type a question such as `What was the dispatch-down risk at 2026-01-24 01:00?`. The reply card shows the answer and tools used; a dispatch-down question also opens the historical replay view. For a future constraint outlook, run the checked daily GFS inference job first, then ask about upcoming national constraint or a specific UTC half-hour. If the snapshot is missing or expired, the chat tool reports it as unavailable. National forecasts alone cannot justify a location-specific operator action.

Candidate actions come from `config/operator_actions.txt`. To switch model, change `AZURE_OPENAI_DEPLOYMENT` in `.env` (`gpt-4.1`, `gpt-4.1-mini` or `gpt-4o`) and restart the API. A `429` response means the shared Azure endpoint is rate-limited; wait and retry.

### Getting into the azure vm
```bash
az ssh vm -n vm-hack-team12 -g rg-hack-team12-swc
```

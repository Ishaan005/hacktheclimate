# Golden-path demo

The demo is intentionally narrow. It uses a small synthetic four-bus planning
case packaged in the backend so a fresh clone can exercise the real DC solver,
action contract and bundle engine without the external TYTFS working files.

## Start the teammate demo

Clone the repository and check out `feat/golden-path-demo` (PR #60). To use
Azure OpenAI for the existing intake step, first fetch your team credentials into a
git-ignored `.env` using Azure CLI and Python 3.11:

```bash
az login --tenant 6c51c659-9d52-41af-81f7-dde16380e813
az account set --subscription eb517801-6c35-40b5-8651-3fea5cc570b0
python3.11 -m scripts.fetch_azure_openai_env
```

On Windows, use `py -3.11 -m scripts.fetch_azure_openai_env` for the last
command. A clone never contains the Azure key.

The easiest cross-platform app route is Docker Desktop or Docker Engine. From
the repository root:

```bash
docker build -t htc-golden-demo .
docker run --rm --env-file .env -p 8000:8000 htc-golden-demo
```

Open <http://127.0.0.1:8000/>. The container serves both the built UI and API;
it does not need local Python or Node after `.env` is prepared. Docker must be
installed and running. If Azure access is unavailable, omit `--env-file .env`:
the computed case still works using rule-based intake.

For local development without Docker, use Python 3.11 and Node 22. From the
repository root on macOS or Linux, install once and run the preflight:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-chat.txt
cd frontend && npm ci && cd ..
.venv/bin/python -m scripts.check_demo_ready
```

Start the API and UI in separate terminals from the repository root:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/>. Keep the UI in its default API mode; fixture
mode uses invented screen fixtures and does not run this backend path. The
computed case needs no Azure credentials, external planning files or current
GFS snapshot. Azure intake needs the `.env` prepared above. If the page
has an earlier case, enter either prompt in the top situation box to replace it.

On Windows PowerShell, use `py -3.11 -m venv .venv`, then
`.\.venv\Scripts\python.exe` in place of `.venv/bin/python` in the commands
above. Run `npm ci` and `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`
from `frontend` in a second PowerShell window. Docker is the simpler Windows
path because it serves both pieces on port 8000.

## Hero prompt

Paste this into the existing situation box:

> Planned outage in the west is causing a line overload. High wind around Ballylickey is constrained for the next 2 hours. What can we do to reduce dispatch-down?

The intake layer should extract:

- local network constraint
- planned outage exposure
- event window: next 2 hours
- affected area: West

After fact review, **Evaluate actions** runs the backend-owned golden path.
The review should show local network limit and planned outage, `next 2 hours`,
and `West`. The screen should then say **Demo planning case** and **Modeled
candidate**.
With Azure configured, the existing intake step calls Azure OpenAI. If its
extraction agrees with the checked demo facts, fact review says **Read by the
language model**. If it differs or Azure is unavailable, intake uses the same
checked facts from rules. The workspace layout stays the same.

Expected story:

1. Baseline planned-outage export line is about **109.1% of rate A**.
2. 10 MW flexible demand alone captures renewable energy but does not relieve
   the export bottleneck.
3. 15 MW redispatch alone relieves the bottleneck but gets no renewable-capture
   credit.
4. The combined bundle reduces the modeled export line to about **81.8%** and
   has a **20 MWh modeled renewable-capture upper bound** over the two-hour
   window.
5. The UI labels it **Modeled candidate**, not a validated recommendation.
6. The 40 MWh → 20 MWh dispatch-down view is a **demo scenario assumption**
   using that capture upper bound, not a validated locational forecast.

## Refusal variant

Use:

> Planned outage in the west near Ballylickey plus another credible circuit loss creates an N-1 overload for the next 2 hours.

This resolves to T4. The additional synthetic circuit loss islands the West
demo area, so the action disappears and the UI explains why no modeled
candidate survives.

Use this second case to show that a failed network screen removes the
candidate. Re-enter the hero prompt to return to the positive case.

## Preflight

Run:

```bash
.venv/bin/python -m scripts.check_demo_ready
```

It must end with:

```text
DEMO READY
```

## What is real vs synthetic

**Calculated live by project code**

- scenario/action contract eligibility
- action-bundle generation
- DC network flows
- planned-outage topology
- mixed flexible-demand + redispatch network effect
- thermal/islanding checks

**Synthetic demo inputs / assumptions**

- the four-bus operating case and asset names
- action availability/capability
- the national constraint numbers for the two-hour window
- treating the 20 MWh capture upper bound as the demo post-action
  dispatch-down reduction

Do not present this as the current Irish operating grid or as an operational
instruction. It is a planning-case demonstration of the product workflow.

## What comes with a clone

The golden path is packaged in tracked backend source and configuration. It
does not read `data/raw/`, `data/inference/`, Azure credentials, or a local
TYTFS case. The repository also tracks the processed datasets, saved models,
metrics, source manifests, and audit documentation used by other project paths.

Azure intake needs the teammate's own Key Vault credentials and network
access. No key or generated model output is committed. Direct questions typed
into the existing situation box use the existing `/v1/chat` route.

Original workbooks and raw downloads remain outside Git or under ignored
`data/raw/`; generated current inference snapshots under `data/inference/` are
also ignored. Those are not needed for this demo. Other live or planning routes
can still report unavailable until their separately reviewed inputs exist.

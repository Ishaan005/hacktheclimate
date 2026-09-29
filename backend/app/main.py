from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .demo import router as demo_router
from .decision.routes import router as decision_router
from .gfs_forecast import DEFAULT_OUTPUT_DIR, load_current_forecast
from .dispatch_down.routes import router as dispatch_down_router
from .network_forecast import build_network_forecast_from_files
from .network import load_case
from .network_actions import load_action_candidates
from .network_forecast import DEFAULT_CASE_DIR, DEFAULT_CROSSWALK_PATH, DEFAULT_INPUT_PATH, DEFAULT_PLANNED_OUTAGE, load_forecast_inputs, load_reviewed_crosswalk
from .operator_view import build_operator_view
from .operator_evaluation import OperatorEvaluationRequest, evaluate_operator_case
from .proxy import add_pressure_proxy

from .constraints.routes import router as constraint_router
from .intake import router as intake_router

try:  # chat is optional: install requirements-chat.txt to enable it
    from .chat.routes import router as chat_router
except ImportError:  # pragma: no cover
    chat_router = None

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

app = FastAPI(title="Team Blue — Hack the Climate API", version="0.1.0")
app.include_router(demo_router)
app.include_router(decision_router)
app.include_router(dispatch_down_router)
app.include_router(constraint_router)
app.include_router(intake_router)
if chat_router is not None:
    app.include_router(chat_router)
DATA = Path("data/processed/canonical_ie.csv")
LABELED_DATA = Path("data/processed/training_table_labeled_jan2026.csv")
GFS_FORECAST_PATH = DEFAULT_OUTPUT_DIR / "latest.json"


def _json_records(df: pd.DataFrame, cols: list[str], limit: int) -> list[dict]:
    sample = df[cols].tail(max(1, min(limit, 336)))
    return sample.astype(object).where(pd.notna(sample), None).to_dict(orient="records")

@app.get("/health")
def health():
    return {"status": "ok", "canonical_data_exists": DATA.exists()}


@app.get("/v1/sample/pressure")
def sample_pressure(limit: int = 48):
    if not DATA.exists():
        raise HTTPException(404, "Run scripts/build_canonical.py first")
    df = pd.read_csv(DATA, parse_dates=["timestamp"])
    df = add_pressure_proxy(df)
    cols = [
        "timestamp",
        "load_mw",
        "wind_onshore_mw",
        "solar_mw",
        "renewable_vre_share",
        "residual_load_mw",
        "sem_price_currency_per_mwh",
        "pressure_proxy",
    ]
    return _json_records(df, cols, limit)


@app.get("/v1/sample/dispatch-down")
def sample_dispatch_down(limit: int = 96):
    if not LABELED_DATA.exists():
        raise HTTPException(404, "Build data/processed/training_table_labeled_jan2026.csv first")
    df = pd.read_csv(LABELED_DATA, parse_dates=["timestamp"])
    cols = [
        "timestamp", "dispatch_down_total_mwh", "constraint_mwh", "curtailment_mwh",
        "wind_dispatch_down_total_mwh", "solar_dispatch_down_total_mwh",
        "eirgrid_snsp_pct", "eirgrid_ie_demand_mw", "eirgrid_ie_wind_availability_mw",
        "eirgrid_ewic_ic_mw", "eirgrid_greenlink_ic_mw", "sem_price_currency_per_mwh",
    ]
    cols = [c for c in cols if c in df.columns]
    return _json_records(df, cols, limit)


@app.get("/v1/network/forecast")
def network_forecast():
    """Return 48 half-hour national + network constraint forecast records."""
    try:
        return build_network_forecast_from_files(as_of=datetime.now(timezone.utc))
    except FileNotFoundError as exc:
        raise HTTPException(
            503,
            "Network forecast inputs are not prepared. Import the TYTFS case and provide "
            "NETWORK_FORECAST_INPUT plus NETWORK_GENERATOR_CROSSWALK.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/operator/view")
def operator_view():
    """Expose future scenario and action screens with explicit data gaps."""
    action_path = Path(os.getenv("NETWORK_ACTION_CANDIDATES", REPO_ROOT / "data/processed/network_action_candidates.json"))
    try:
        case = load_case(DEFAULT_CASE_DIR)
        rows = load_forecast_inputs(DEFAULT_INPUT_PATH, as_of=datetime.now(timezone.utc))
        crosswalk = load_reviewed_crosswalk(DEFAULT_CROSSWALK_PATH)
        catalog_available = action_path.is_file()
        candidates = load_action_candidates(action_path) if catalog_available else []
        return build_operator_view(
            case, rows, crosswalk, candidates,
            action_catalog_available=catalog_available,
            planned_outage=DEFAULT_PLANNED_OUTAGE,
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, f"Required operator input is missing: {exc.filename}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/v1/operator/evaluate")
def operator_evaluate(request: OperatorEvaluationRequest):
    """Evaluate supplied point-in-time conditions and actions on the local case."""
    if request.decision_case.as_of > datetime.now(timezone.utc):
        raise HTTPException(422, "case decision time cannot be in the future")
    try:
        return evaluate_operator_case(
            request, load_case(DEFAULT_CASE_DIR),
            load_reviewed_crosswalk(DEFAULT_CROSSWALK_PATH),
            planned_outage=DEFAULT_PLANNED_OUTAGE,
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, f"Required planning case input is missing: {exc.filename}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/v1/forecast/constraint")
def national_constraint_forecast():
    """Serve only future rows from the latest checked national GFS forecast."""
    try:
        return load_current_forecast(GFS_FORECAST_PATH)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, f"Checked national forecast unavailable: {exc}") from exc


if FRONTEND_DIST.is_dir():
    @app.get("/")
    def root():
        return FileResponse(FRONTEND_DIST / "index.html")

    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIST, html=True),
        name="frontend",
    )

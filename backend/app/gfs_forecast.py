"""Checked national GFS constraint inference and read-only forecast serving.

The writer fetches one pinned 00Z weather issue, checks every NOAA source
forecast hour, and atomically publishes a versioned result. API requests read
that result; they never fetch weather or run a model in the request path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from scripts.fetch_gfs_daily_panel import fetch_day, normalize
from scripts.train_gfs_constraint import (
    build_forecast_rows,
    predict_one,
    validate_release_manifest,
)
from scripts.verify_gfs_source_availability import inspect_one


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path(os.getenv("GFS_FORECAST_DIR", REPO_ROOT / "data/inference/gfs_constraint"))
DEFAULT_MODEL = REPO_ROOT / "artifacts/gfs_constraint/final_model.joblib"
DEFAULT_METRICS = REPO_ROOT / "artifacts/gfs_constraint/metrics.json"
DEFAULT_TRAIN_POINT_MANIFEST = REPO_ROOT / "data/processed/gfs_daily_2026_jan_aug_manifest.json"
LIMITATIONS = [
    "Research candidate: August expected-MWh MAE did not beat a zero forecast.",
    "National constraint forecast only; no curtailment, network location, safety or avoided-energy claim.",
    "NOAA S3 Last-Modified is an availability proxy, not a live ingestion SLA.",
]


def _utc(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("Forecast times must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_due_issue(now: datetime) -> datetime:
    """Select the newest daily 00Z cycle whose 06Z decision has passed."""
    now = _utc(now)
    issue = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return issue if now.hour >= 6 else issue - timedelta(days=1)


def _check_window(issue: datetime, now: datetime) -> datetime:
    issue, now = _utc(issue), _utc(now)
    if (issue.hour, issue.minute, issue.second, issue.microsecond) != (0, 0, 0, 0):
        raise ValueError("Inference requires a daily 00Z GFS issue")
    decision = issue + timedelta(hours=6)
    if not decision <= now < decision + timedelta(hours=24):
        raise ValueError("Issue is not within its 06Z-to-next-06Z forecast window")
    return decision


def build_snapshot(
    panel: pd.DataFrame,
    point_manifest: dict[str, Any],
    release_manifest: dict[str, Any],
    *,
    model_path: Path,
    metrics_path: Path,
    now: datetime,
) -> dict[str, Any]:
    """Validate one weather vintage and score the saved forecast-safe model."""
    if panel.empty or panel.issue_time_utc.nunique() != 1:
        raise ValueError("Inference requires exactly one GFS issue")
    issue = _utc(str(panel.issue_time_utc.iloc[0]))
    now = _utc(now)
    decision = _check_window(issue, now)
    if len(panel) != 25 or sorted(panel.lead_hours.tolist()) != list(range(6, 31)):
        raise ValueError("GFS issue must have exactly forecast hours 6-30")
    if len(point_manifest.get("days", [])) != 1 or len(release_manifest.get("days", [])) != 1:
        raise ValueError("Source manifests must describe exactly one issue")
    if _utc(point_manifest["days"][0]["issue_time"]) != issue:
        raise ValueError("Point manifest issue differs from weather panel")
    training_points = json.loads(DEFAULT_TRAIN_POINT_MANIFEST.read_text())
    for key in ("product", "units", "point_selection"):
        if point_manifest.get(key) != training_points.get(key):
            raise ValueError(f"Live GFS {key} differs from training")
    snapshot_ids = point_manifest.get("snapshot_ids", [])
    if len(snapshot_ids) != 1 or set(panel.source_snapshot_id) != set(snapshot_ids):
        raise ValueError("GFS point responses do not share one source snapshot")
    if _utc(point_manifest["days"][0]["retrieved_at_utc"]) > now:
        raise ValueError("Weather API retrieval is later than the inference run")

    # validate_release_manifest reads a path so the same all-lead rule applies
    # in historical training and operational inference.
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        release_path = Path(temporary) / "release.json"
        release_path.write_text(json.dumps(release_manifest))
        validate_release_manifest(panel, release_path)

    available = _utc(str(panel.source_available_at_utc.iloc[0]))
    if available > decision:
        raise ValueError("NOAA source was not available by the decision time")
    bundle = joblib.load(model_path)
    if not {"model", "calendar_baseline", "source_versions"} <= set(bundle):
        raise ValueError("Saved model is missing expected training metadata")
    metrics = json.loads(metrics_path.read_text())
    if bundle["source_versions"] != metrics["source_versions"]:
        raise ValueError("Saved model and evaluation report have different source versions")
    rows, features = build_forecast_rows(panel)
    if len(rows) != 48 or bundle["model"]["features"] != features:
        raise ValueError("Live feature schema differs from the trained model")
    primary = predict_one(bundle["model"], rows)
    calendar = predict_one(bundle["calendar_baseline"], rows)
    forecasts = []
    for index, row in rows.iterrows():
        scored = primary.loc[index]
        reference = calendar.loc[index]
        entry = {
            "target_time_utc": _iso(row.target_time_utc.to_pydatetime().replace(tzinfo=timezone.utc)),
            "weather_valid_time_utc": _iso(row.valid_time_utc.to_pydatetime().replace(tzinfo=timezone.utc)),
            "horizon_hours": float(row.horizon_hours),
            "event_probability": float(scored.probability),
            "expected_constraint_mwh": float(scored.expected_mwh),
            "lower_80_mwh": float(scored.lower_80_mwh),
            "upper_80_mwh": float(scored.upper_80_mwh),
            "lower_90_mwh": float(scored.lower_90_mwh),
            "upper_90_mwh": float(scored.upper_90_mwh),
            "calendar_event_probability": float(reference.probability),
            "calendar_expected_constraint_mwh": float(reference.expected_mwh),
        }
        forecasts.append(entry)
    august = metrics["folds"]["2026-08"]["all_horizons"]
    point_day = point_manifest["days"][0]
    release_day = release_manifest["days"][0]
    snapshot = {
        "schema_version": 1,
        "status": "experimental",
        "generated_at_utc": _iso(now),
        "issue_time_utc": _iso(issue),
        "decision_time_utc": _iso(decision),
        "forecast_end_utc": _iso(decision + timedelta(hours=24)),
        "source": {
            "product": point_manifest["product"],
            "snapshot_id": str(rows.source_snapshot_id.iloc[0]),
            "api_retrieved_at_utc": point_day["retrieved_at_utc"],
            "api_response_sha256": point_day["api_sha256"],
            "noaa_last_required_object_at_utc": _iso(available),
            "noaa_lead_hours_checked": list(range(6, 31)),
            "noaa_lead_objects": release_day["lead_objects"],
            "selected_points": point_manifest["point_selection"],
            "point_urls": point_day["site_sources"],
            "point_manifest_sha256": hashlib.sha256(json.dumps(point_manifest, sort_keys=True).encode()).hexdigest(),
            "release_manifest_sha256": hashlib.sha256(json.dumps(release_manifest, sort_keys=True).encode()).hexdigest(),
        },
        "model": {
            "name": "gfs_constraint_final_candidate",
            "artifact_sha256": _sha256(model_path),
            "training_source_versions": bundle["source_versions"],
            "train_target_end": bundle["model"]["train_target_end"],
            "calibration_target_end": bundle["model"]["calibration_target_end"],
            "august_holdout_mae_mwh": august["expected_mae_mwh"],
            "august_zero_mae_mwh": august["zero_mae_mwh"],
        },
        "limitations": LIMITATIONS,
        "forecasts": forecasts,
    }
    validate_snapshot(snapshot, as_of=now)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any], *, as_of: datetime) -> list[dict[str, Any]]:
    """Reject malformed, old or exhausted snapshots; return future rows only."""
    as_of = _utc(as_of)
    if snapshot.get("schema_version") != 1 or snapshot.get("status") != "experimental":
        raise ValueError("Unknown national forecast snapshot schema or status")
    issue = _utc(snapshot["issue_time_utc"])
    decision = _utc(snapshot["decision_time_utc"])
    generated = _utc(snapshot["generated_at_utc"])
    source_time = _utc(snapshot["source"]["noaa_last_required_object_at_utc"])
    api_retrieved = _utc(snapshot["source"]["api_retrieved_at_utc"])
    if decision != issue + timedelta(hours=6) or source_time > decision:
        raise ValueError("Forecast source was not available for its decision")
    if generated < decision or generated > as_of or as_of >= decision + timedelta(hours=24):
        raise ValueError("National forecast snapshot is stale or not yet valid")
    if api_retrieved > generated:
        raise ValueError("Weather API retrieval is later than forecast generation")
    if _utc(snapshot["forecast_end_utc"]) != decision + timedelta(hours=24):
        raise ValueError("Incorrect forecast end time")
    source = snapshot["source"]
    model = snapshot["model"]
    lead_objects = source.get("noaa_lead_objects", [])
    if (source.get("noaa_lead_hours_checked") != list(range(6, 31))
        or sorted(item["lead_hours"] for item in lead_objects) != list(range(6, 31))
        or max(_utc(item["last_modified_utc"]) for item in lead_objects) != source_time
        or not all(item.get("url") and item.get("etag") for item in lead_objects)
        or not source.get("selected_points") or not source.get("point_urls")
    ):
        raise ValueError("Forecast lead or point provenance is incomplete")
    if not all(
        source.get(key) for key in ("snapshot_id", "api_response_sha256", "point_manifest_sha256", "release_manifest_sha256")
    ) or not model.get("artifact_sha256"):
        raise ValueError("Forecast source or model provenance is incomplete")
    rows = snapshot.get("forecasts")
    if not isinstance(rows, list) or len(rows) != 48:
        raise ValueError("National forecast must contain 48 half-hour rows")
    numeric = (
        "event_probability", "expected_constraint_mwh", "lower_80_mwh", "upper_80_mwh",
        "lower_90_mwh", "upper_90_mwh", "calendar_event_probability",
        "calendar_expected_constraint_mwh",
    )
    for index, row in enumerate(rows, start=1):
        target = decision + timedelta(minutes=30 * index)
        if _utc(row["target_time_utc"]) != target or float(row["horizon_hours"]) != index / 2:
            raise ValueError("Forecast target or horizon is misaligned")
        weather_valid = _utc(row["weather_valid_time_utc"])
        if weather_valid != target.replace(minute=0):
            raise ValueError("Weather valid hour is misaligned")
        for key in numeric:
            value = float(row[key])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid forecast value: {key}")
        if row["event_probability"] > 1 or row["calendar_event_probability"] > 1:
            raise ValueError("Forecast probability is outside [0, 1]")
        for coverage in (80, 90):
            if not row[f"lower_{coverage}_mwh"] <= row["expected_constraint_mwh"] <= row[f"upper_{coverage}_mwh"]:
                raise ValueError("Forecast interval does not contain its expected MWh")
    future = [row for row in rows if _utc(row["target_time_utc"]) > as_of]
    if not future:
        raise ValueError("National forecast has no remaining future targets")
    return future


def publish_snapshot(snapshot: dict[str, Any], output_dir: Path) -> Path:
    """Write an immutable run and atomically replace the latest pointer."""
    validate_snapshot(snapshot, as_of=_utc(snapshot["generated_at_utc"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    runs = output_dir / "runs"
    runs.mkdir(exist_ok=True)
    run_id = snapshot["generated_at_utc"].replace(":", "").replace("-", "").replace(".", "")
    run_path = runs / f"{run_id}.json"
    encoded = json.dumps(snapshot, indent=2, allow_nan=False).encode()
    with run_path.open("xb") as stream:
        stream.write(encoded)
    latest = output_dir / "latest.json"
    temporary = output_dir / f".latest-{os.getpid()}-{run_id}.tmp"
    temporary.write_bytes(encoded)
    temporary.replace(latest)
    return run_path


def run_issue(
    *,
    now: datetime | None = None,
    issue: datetime | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    cache_dir: Path = REPO_ROOT / "data/raw/gfs_daily",
    release_cache_dir: Path = REPO_ROOT / "data/raw/gfs_release_checks",
    model_path: Path = DEFAULT_MODEL,
    metrics_path: Path = DEFAULT_METRICS,
) -> Path:
    """Fetch, check, score and publish one daily issue; fail without replacing latest."""
    start = _utc(now or datetime.now(timezone.utc))
    issue = _utc(issue or latest_due_issue(start))
    _check_window(issue, start)
    raw_path = fetch_day(issue, cache_dir)
    panel, point_manifest = normalize([raw_path])
    release_path = inspect_one(issue.strftime("%Y%m%d"), release_cache_dir)
    release_day = json.loads(release_path.read_text())
    panel["source_available_at_utc"] = release_day["source_available_at_utc"]
    release_manifest = {"days": [release_day]}
    snapshot = build_snapshot(
        panel, point_manifest, release_manifest,
        model_path=model_path, metrics_path=metrics_path,
        now=datetime.now(timezone.utc) if now is None else start,
    )
    return publish_snapshot(snapshot, output_dir)


def load_current_forecast(path: Path, *, as_of: datetime | None = None) -> dict[str, Any]:
    """Read the published result and expose only still-future target intervals."""
    now = _utc(as_of or datetime.now(timezone.utc))
    snapshot = json.loads(path.read_text())
    remaining = validate_snapshot(snapshot, as_of=now)
    return {**snapshot, "served_at_utc": _iso(now), "remaining_intervals": len(remaining), "forecasts": remaining}

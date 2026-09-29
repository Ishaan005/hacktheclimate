"""Audit frozen GFS artifacts and write explicit forecast promotion gates.

The default gate covers the national constraint event model. Volume and
curtailment gates are reported separately; a failed gate never becomes a
fabricated total dispatch-down forecast.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import joblib
import pandas as pd

from backend.app.gfs_forecast import validate_snapshot
from scripts.train_gfs_constraint import (
    _sha256,
    build_training_table,
    event_column,
    metrics,
    validate_release_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
MONTHS = tuple(f"2026-{month:02d}" for month in range(4, 9))


def _same_metrics(actual: dict, recorded: dict) -> bool:
    for key, value in actual.items():
        prior = recorded.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if prior is None or not math.isclose(value, prior, abs_tol=1e-9, rel_tol=1e-9):
                return False
        elif prior != value:
            return False
    return True


def audit_target(target: str, panel: pd.DataFrame, labels: pd.DataFrame, release: Path) -> dict:
    name = target.removesuffix("_mwh")
    directory = ROOT / f"artifacts/gfs_{name}"
    report = json.loads((directory / "metrics.json").read_text())
    bundle = joblib.load(directory / "final_model.joblib")
    predictions = pd.read_csv(directory / "backtest_predictions.csv")
    table_path = ROOT / f"data/processed/gfs_{name}_training_2026_jan_aug.csv"
    table, features = build_training_table(panel, labels, target=target)
    source = report["source_versions"]
    hashes = {
        "weather_csv_sha256": ROOT / "data/processed/gfs_daily_2026_jan_aug.csv",
        "labels_csv_sha256": ROOT / "data/processed/training_table_eirgrid_2026_jan_aug.csv",
        "training_table_csv_sha256": table_path,
        "training_script_sha256": ROOT / "scripts/train_gfs_constraint.py",
        "release_manifest_sha256": release,
    }
    provenance = (
        all(source.get(key) == _sha256(path) for key, path in hashes.items())
        and bundle.get("source_versions") == source
        and bundle.get("target", "constraint_mwh") == target
        and report["train_table_rows"] == len(table)
        and len(pd.read_csv(table_path)) == len(table)
    )
    allowed = set(features)
    no_leakage = (
        set(report["features"]) == allowed
        and set(bundle["model"]["features"]) == allowed
        and not any("mwh" in feature or "eirgrid" in feature or "actual" in feature for feature in allowed)
        and table.source_available_at_utc.le(table.decision_time_utc).all()
        and table.decision_time_utc.lt(table.target_time_utc).all()
    )
    if target not in predictions or event_column(target) not in predictions:
        raise ValueError("Held-out predictions omit the selected label or event")
    if not predictions.target_time_utc.is_unique or set(predictions.test_month) != set(MONTHS):
        raise ValueError("Held-out predictions have duplicate targets or missing months")
    predictions["target_time_utc"] = pd.to_datetime(predictions.target_time_utc)
    chronological = True
    metrics_match = True
    event_advantage = True
    volume_months = {}
    for month in MONTHS:
        fold = report["folds"][month]
        group = predictions[predictions.test_month.eq(month)]
        train_end = pd.Timestamp(fold["train_end"])
        calibration_start = pd.Timestamp(fold["calibration_start"])
        calibration_end = pd.Timestamp(fold["calibration_end"])
        test_start = pd.Timestamp(fold["test_start"])
        chronological &= train_end < calibration_start <= calibration_end < test_start
        chronological &= group.target_time_utc.min() == test_start
        chronological &= group.target_time_utc.dt.strftime("%Y-%m").eq(month).all()
        model = group.filter(regex="^model_").rename(columns=lambda c: c.removeprefix("model_"))
        calendar = group.filter(regex="^calendar_").rename(columns=lambda c: c.removeprefix("calendar_"))
        observed = metrics(group, model, calendar, target=target)
        metrics_match &= _same_metrics(observed, fold["all_horizons"])
        event_advantage &= observed["event_pr_auc"] > observed["calendar_event_pr_auc"]
        volume_months[month] = observed["expected_mae_mwh"] < observed["zero_mae_mwh"]
    model = predictions.filter(regex="^model_").rename(columns=lambda c: c.removeprefix("model_"))
    calendar = predictions.filter(regex="^calendar_").rename(columns=lambda c: c.removeprefix("calendar_"))
    pooled = metrics(predictions, model, calendar, target=target)
    metrics_match &= _same_metrics(pooled, report["aggregate_backtest"]["all_horizons"])
    event_advantage &= pooled["event_pr_auc"] > pooled["calendar_event_pr_auc"]
    calibration_measured = all(
        math.isfinite(pooled[key]) and 0 <= pooled[key] <= 1
        for key in ("event_ece_10_bins", "interval_80_coverage", "interval_90_coverage")
    )
    hard = bool(provenance and no_leakage and chronological and metrics_match and calibration_measured)
    return {
        "target": target,
        "model_sha256": _sha256(directory / "final_model.joblib"),
        "checks": {
            "source_and_artifact_integrity": bool(provenance),
            "forecast_safe_features": bool(no_leakage),
            "chronological_holdout": bool(chronological),
            "heldout_metrics_recomputed": bool(metrics_match),
            "calibration_and_interval_coverage_measured": bool(calibration_measured),
            "event_pr_auc_beats_calendar_each_month_and_pooled": bool(event_advantage),
            "volume_mae_beats_zero_each_month": bool(all(volume_months.values())),
            "volume_mae_beats_zero_pooled": bool(pooled["expected_mae_mwh"] < pooled["zero_mae_mwh"]),
        },
        "volume_months_beating_zero": volume_months,
        "pooled": pooled,
        "event_ready_for_demo": bool(hard and event_advantage),
        "volume_ready_for_demo": bool(hard and event_advantage and all(volume_months.values()) and pooled["expected_mae_mwh"] < pooled["zero_mae_mwh"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/gfs_model_readiness.json")
    parser.add_argument("--snapshot", type=Path, help="Optional current inference snapshot to check for staleness")
    parser.add_argument("--require", choices=("constraint_event", "constraint_volume", "curtailment", "total", "live"), default="constraint_event")
    args = parser.parse_args()
    weather = ROOT / "data/processed/gfs_daily_2026_jan_aug.csv"
    release = ROOT / "data/processed/gfs_daily_2026_jan_aug_release_manifest.json"
    panel = pd.read_csv(weather)
    labels = pd.read_csv(ROOT / "data/processed/training_table_eirgrid_2026_jan_aug.csv")
    validate_release_manifest(panel, release)
    results = {}
    for target in ("constraint_mwh", "curtailment_mwh"):
        key = target.removesuffix("_mwh")
        try:
            results[key] = audit_target(target, panel, labels, release)
        except (KeyError, ValueError, OSError, TypeError) as exc:
            results[key] = {"target": target, "error": str(exc), "event_ready_for_demo": False, "volume_ready_for_demo": False}
    live = {"checked": bool(args.snapshot), "valid": False}
    if args.snapshot:
        try:
            snapshot = json.loads(args.snapshot.read_text())
            live["remaining_intervals"] = len(validate_snapshot(snapshot, as_of=datetime.now(timezone.utc)))
            if snapshot["model"]["artifact_sha256"] != results["constraint"].get("model_sha256"):
                raise ValueError("Live snapshot uses a different constraint model artifact")
            live["valid"] = True
        except (KeyError, ValueError, OSError, TypeError) as exc:
            live["error"] = str(exc)
    constraint = results["constraint"]
    curtailment = results["curtailment"]
    gates = {
        "constraint_event": constraint["event_ready_for_demo"],
        "constraint_volume": constraint["volume_ready_for_demo"],
        "curtailment": curtailment["volume_ready_for_demo"],
        "total": constraint["volume_ready_for_demo"] and curtailment["volume_ready_for_demo"],
        "live": constraint["event_ready_for_demo"] and live["valid"],
    }
    output = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_contract": "00Z NOAA GFS issue; 06:00 UTC decision; 48 future half-hours",
        "model_status": "experimental national forecast; no locational, safety or avoided-energy inference",
        "targets": results,
        "live_snapshot": live,
        "gates": gates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {args.output}")
    for name, passed in gates.items():
        print(f"{name}: {'PASS' if passed else 'UNAVAILABLE'}")
    if not gates[args.require]:
        raise SystemExit(f"Required model gate failed: {args.require}")


if __name__ == "__main__":
    main()

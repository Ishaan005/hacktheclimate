from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pytest

from backend.app import gfs_forecast


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 31, hour, minute, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def checked_snapshot() -> dict:
    root = gfs_forecast.REPO_ROOT
    panel = pd.read_csv(root / "data/processed/gfs_daily_2026_jan_aug.csv")
    panel = panel[panel.issue_time_utc.eq("2026-08-31T00:00:00Z")].copy()
    point = json.loads((root / "data/processed/gfs_daily_2026_jan_aug_manifest.json").read_text())
    point["days"] = [day for day in point["days"] if day["issue_time"] == "2026-08-31T00:00:00Z"]
    point["days"][0]["retrieved_at_utc"] = "2026-08-31T06:10:00Z"
    release = json.loads((root / "data/processed/gfs_daily_2026_jan_aug_release_manifest.json").read_text())
    release["days"] = [day for day in release["days"] if day["issue_time_utc"] == "2026-08-31T00:00:00Z"]
    return gfs_forecast.build_snapshot(
        panel, point, release, model_path=gfs_forecast.DEFAULT_MODEL,
        metrics_path=gfs_forecast.DEFAULT_METRICS, now=utc(6, 15),
    )


def test_due_issue_is_yesterday_before_06z() -> None:
    assert gfs_forecast.latest_due_issue(utc(5, 59)) == utc(0) - timedelta(days=1)
    assert gfs_forecast.latest_due_issue(utc(6)) == utc(0)


def test_checked_snapshot_publishes_and_serves_only_future_rows(checked_snapshot, tmp_path) -> None:
    run_path = gfs_forecast.publish_snapshot(checked_snapshot, tmp_path)
    assert run_path.exists()
    current = gfs_forecast.load_current_forecast(tmp_path / "latest.json", as_of=utc(19, 45))
    assert current["status"] == "experimental"
    assert current["remaining_intervals"] == 21
    assert current["forecasts"][0]["target_time_utc"] == "2026-08-31T20:00:00.000000Z"
    assert current["model"]["august_holdout_mae_mwh"] > current["model"]["august_zero_mae_mwh"]
    assert len(json.loads(run_path.read_text())["forecasts"]) == 48


def test_source_after_decision_is_rejected(checked_snapshot) -> None:
    late = deepcopy(checked_snapshot)
    late["source"]["noaa_last_required_object_at_utc"] = "2026-08-31T06:01:00Z"
    with pytest.raises(ValueError, match="not available"):
        gfs_forecast.validate_snapshot(late, as_of=utc(6, 15))


def test_missing_lead_provenance_is_rejected(checked_snapshot) -> None:
    incomplete = deepcopy(checked_snapshot)
    incomplete["source"]["noaa_lead_hours_checked"].pop()
    with pytest.raises(ValueError, match="provenance"):
        gfs_forecast.validate_snapshot(incomplete, as_of=utc(6, 15))


def test_exhausted_forecast_is_rejected(checked_snapshot, tmp_path) -> None:
    gfs_forecast.publish_snapshot(checked_snapshot, tmp_path)
    with pytest.raises(ValueError, match="stale"):
        gfs_forecast.load_current_forecast(tmp_path / "latest.json", as_of=utc(6) + timedelta(days=1))


def test_failed_fetch_preserves_last_published_forecast(checked_snapshot, tmp_path, monkeypatch) -> None:
    gfs_forecast.publish_snapshot(checked_snapshot, tmp_path)
    original = (tmp_path / "latest.json").read_bytes()

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("weather source unavailable")

    monkeypatch.setattr(gfs_forecast, "fetch_day", unavailable)
    with pytest.raises(RuntimeError, match="unavailable"):
        gfs_forecast.run_issue(now=utc(6, 20), output_dir=tmp_path)
    assert (tmp_path / "latest.json").read_bytes() == original


def test_invalid_prediction_is_rejected(checked_snapshot) -> None:
    broken = deepcopy(checked_snapshot)
    broken["forecasts"][0]["expected_constraint_mwh"] = float("nan")
    with pytest.raises(ValueError, match="Invalid forecast"):
        gfs_forecast.validate_snapshot(broken, as_of=utc(6, 15))

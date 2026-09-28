from __future__ import annotations

import json
import pandas as pd
import pytest

from scripts.train_gfs_constraint import build_training_table, evaluate_fold, fit_bundle, validate_release_manifest


def sample_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    weather = []
    labels = []
    for day in ("2026-01-24", "2026-01-25"):
        issue = pd.Timestamp(day, tz="UTC")
        for lead in range(6, 31):
            weather.append({
                "issue_time_utc": issue,
                "decision_time_utc": issue + pd.Timedelta(hours=6),
                "source_available_at_utc": issue + pd.Timedelta(hours=4),
                "valid_time_utc": issue + pd.Timedelta(hours=lead),
                "lead_hours": lead,
                "source_snapshot_id": "test-snapshot",
                "donegal_wind_speed_100m": float(lead),
            })
        for half_hour in range(1, 49):
            target = issue + pd.Timedelta(hours=6) + pd.Timedelta(minutes=30 * half_hour)
            labels.append({"timestamp": target, "constraint_mwh": float(half_hour % 9), "curtailment_mwh": 0.0})
    return pd.DataFrame(weather), pd.DataFrame(labels)


def test_half_hour_mapping_has_unique_future_targets_and_no_late_weather() -> None:
    weather, labels = sample_frames()
    table, features = build_training_table(weather, labels)
    assert len(table) == 96
    assert table.target_time_utc.is_unique
    assert table.source_available_at_utc.le(table.decision_time_utc).all()
    assert table.valid_time_utc.le(table.target_time_utc).all()
    assert table.decision_time_utc.lt(table.target_time_utc).all()
    assert "constraint_mwh" not in features
    assert "curtailment_mwh" not in features
    first = table.iloc[0]
    assert first.target_time_utc == pd.Timestamp("2026-01-24 06:30")
    assert first.valid_time_utc == pd.Timestamp("2026-01-24 06:00")


def test_weather_arriving_after_decision_is_rejected() -> None:
    weather, labels = sample_frames()
    weather.loc[0, "source_available_at_utc"] = pd.Timestamp("2026-01-24 07:00", tz="UTC")
    with pytest.raises(ValueError, match="after decision"):
        build_training_table(weather, labels)


def test_missing_forecast_hour_is_rejected() -> None:
    weather, labels = sample_frames()
    weather = weather[~((weather.issue_time_utc == pd.Timestamp("2026-01-24", tz="UTC")) & weather.lead_hours.eq(7))]
    with pytest.raises(ValueError, match="Missing forecast hour"):
        build_training_table(weather, labels)


def test_overlapping_train_and_calibration_targets_are_rejected() -> None:
    weather, labels = sample_frames()
    table, features = build_training_table(weather, labels)
    with pytest.raises(ValueError, match="overlap"):
        fit_bundle(table, table, features)


def test_overlapping_calibration_and_test_targets_are_rejected() -> None:
    weather, labels = sample_frames()
    table, features = build_training_table(weather, labels)
    train = table.iloc[:48]
    calibration = table.iloc[48:]
    with pytest.raises(ValueError, match="overlap"):
        evaluate_fold(train, calibration, calibration, features)


def test_release_manifest_must_cover_every_hour_and_match_panel(tmp_path) -> None:
    weather, _ = sample_frames()
    weather["issue_time_utc"] = weather.issue_time_utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    weather["source_available_at_utc"] = weather.source_available_at_utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    days = []
    for issue, group in weather.groupby("issue_time_utc"):
        days.append({"issue_time_utc": issue, "source_available_at_utc": group.source_available_at_utc.iloc[0],
                     "lead_objects": [{"lead_hours": lead, "last_modified_utc": group.source_available_at_utc.iloc[0]}
                                      for lead in range(6, 31)]})
    path = tmp_path / "release.json"
    path.write_text(json.dumps({"days": days}))
    validate_release_manifest(weather, path)
    days[0]["lead_objects"].pop()
    path.write_text(json.dumps({"days": days}))
    with pytest.raises(ValueError, match="lacks forecast hours"):
        validate_release_manifest(weather, path)

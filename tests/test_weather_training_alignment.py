import pandas as pd

from scripts.train_weather_forecast import prepare_weather_frame


def test_weather_join_uses_only_forecasts_available_at_decision_time():
    labels = pd.DataFrame({
        "timestamp": ["2026-09-28T16:00:00Z", "2026-09-28T16:30:00Z"],
        "dispatch_down_total_mwh": [0.0, 12.0],
    })
    forecasts = pd.DataFrame({
        "provider": ["azure_maps"] * 3,
        "location_id": ["galway"] * 3,
        "valid_time_utc": ["2026-09-28T16:00:00Z"] * 3,
        "retrieved_at_utc": [
            "2026-09-27T15:00:00Z",
            "2026-09-27T16:15:00Z",
            "2026-09-27T17:00:00Z",
        ],
        "wind_speed_mps": [3.0, 4.0, 99.0],
    })
    frame, _ = prepare_weather_frame(labels, forecasts, location_id="galway")
    assert frame["wind_speed_mps"].tolist() == [3.0, 4.0]
    assert frame["decision_time_utc"].tolist() == [
        pd.Timestamp("2026-09-27T16:00:00Z"),
        pd.Timestamp("2026-09-27T16:30:00Z"),
    ]
    assert frame["weather_valid_hour_utc"].nunique() == 1


def test_weather_join_drops_stale_forecasts():
    labels = pd.DataFrame({
        "timestamp": ["2026-09-28T16:00:00Z"],
        "dispatch_down_total_mwh": [5.0],
    })
    forecasts = pd.DataFrame({
        "provider": ["azure_maps"],
        "location_id": ["galway"],
        "valid_time_utc": ["2026-09-28T16:00:00Z"],
        "retrieved_at_utc": ["2026-09-27T09:00:00Z"],
        "wind_speed_mps": [3.0],
    })
    frame, _ = prepare_weather_frame(labels, forecasts, location_id="galway", max_age_hours=6)
    assert pd.isna(frame.loc[0, "wind_speed_mps"])

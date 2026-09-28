import pandas as pd

from scripts.forward_constraint import prepare_forecast_frame


def test_network_forecast_features_use_latest_forecast_available_at_decision_time():
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01 00:00:00",
                    "2026-01-01 00:30:00",
                    "2026-01-01 01:00:00",
                    "2026-01-01 01:30:00",
                    "2026-01-01 02:00:00",
                ]
            ),
            "constraint_mwh": [0.0, 1.0, 2.0, 3.0, 4.0],
            "curtailment_mwh": [0.0] * 5,
            "eirgrid_ie_demand_mw": [3000.0] * 5,
            "eirgrid_ie_wind_availability_mw": [1000.0] * 5,
        }
    )
    network = pd.DataFrame(
        {
            "issue_time": pd.to_datetime(
                [
                    "2025-12-31 23:00:00Z",  # safe for the 00:00 decision
                    "2026-01-01 00:15:00Z",  # future-issued, must not leak
                    "2026-01-01 00:15:00Z",  # safe for the 00:30 decision
                ],
                utc=True,
            ),
            "valid_time": pd.to_datetime(
                [
                    "2026-01-01 01:00:00Z",
                    "2026-01-01 01:00:00Z",
                    "2026-01-01 01:30:00Z",
                ],
                utc=True,
            ),
            "max_dc_loading_proxy_pct": [71.0, 99.0, 82.0],
            "minimum_headroom_proxy_mw": [120.0, 1.0, 50.0],
            "n_assets_above_80pct": [0, 7, 2],
        }
    )

    frame, features, _ = prepare_forecast_frame(
        raw,
        horizon_hours=1.0,
        network_forecast_df=network,
    )

    loading = "network_max_dc_loading_proxy_pct_target"
    headroom = "network_minimum_headroom_proxy_mw_target"
    breached = "network_n_assets_above_80pct_target"
    assert {loading, headroom, breached} <= set(features)

    # 00:00 -> 01:00 may use only the 23:00-issued network forecast, never 00:15.
    assert frame.loc[0, loading] == 71.0
    assert frame.loc[0, headroom] == 120.0
    assert frame.loc[0, breached] == 0.0

    # 00:30 -> 01:30 may use the 00:15-issued forecast.
    assert frame.loc[1, loading] == 82.0
    assert frame.loc[1, headroom] == 50.0
    assert frame.loc[1, breached] == 2.0

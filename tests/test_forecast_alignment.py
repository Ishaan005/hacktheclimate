import pandas as pd

from scripts.train_real_baseline import add_one_hour_target


def test_one_hour_target_excludes_gaps_and_uses_target_time_for_split():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-01-23 22:30", "2026-01-23 23:00", "2026-01-23 23:30",
            "2026-01-24 00:00", "2026-01-24 01:00",
        ]),
        "dispatch_down_total_mwh": [1, 2, 3, 4, 5],
    })
    ahead = add_one_hour_target(df)
    assert ahead.loc[1, "target_1h_mwh"] == 4
    assert ahead.loc[1, "target_1h_timestamp"] == pd.Timestamp("2026-01-24 00:00")
    assert ahead.loc[1, "target_1h_timestamp"] >= pd.Timestamp("2026-01-24")
    assert pd.isna(ahead.loc[2, "target_1h_mwh"])  # The next row is 90 minutes away.

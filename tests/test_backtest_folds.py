import pandas as pd

from scripts.backtest_1h_operational import fold_masks


def test_fold_uses_label_time_and_keeps_boundary_out_of_training():
    frame = pd.DataFrame({
        "target_1h_timestamp": pd.to_datetime([
            "2026-03-31 23:30", "2026-04-01 00:00", "2026-04-30 23:30", "2026-05-01 00:00"
        ]),
        "target_1h_mwh": [1.0, 2.0, 3.0, 4.0],
    })
    train, test = fold_masks(frame, pd.Timestamp("2026-04-01"))
    assert train.tolist() == [True, False, False, False]
    assert test.tolist() == [False, True, True, False]

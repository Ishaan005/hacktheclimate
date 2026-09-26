import pandas as pd

from scripts.fetch_eirgrid_context import _path_chunks, _vargen_frame


def test_vargen_current_response_shape_parses_numeric_actual_and_forecast():
    rows = pd.DataFrame({
        "Effective_Date": ["01-01-2026 00:00:00", "01-01-2026 00:15:00"],
        "MW_ACTUAL": ["1326", "1355"],
        "MW_FORECAST": ["964", "964"],
        "Region": ["ROI", "ROI"],
    })
    out = _vargen_frame(rows, "WIND")
    assert out["eirgrid_wind_actual_mw"].tolist() == [1326, 1355]
    assert out["eirgrid_wind_forecast_mw"].tolist() == [964, 964]


def test_path_chunks_keep_each_api_request_within_thirty_days():
    chunks = list(_path_chunks(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-01")))
    assert chunks == [
        (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-31")),
        (pd.Timestamp("2026-01-31"), pd.Timestamp("2026-02-01")),
    ]

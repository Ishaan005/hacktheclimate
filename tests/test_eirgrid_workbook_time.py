import pandas as pd

from scripts.import_eirgrid_qtr_workbook import _irish_local_to_utc


def test_irish_workbook_times_convert_across_spring_clock_change():
    local = pd.Series(pd.to_datetime([
        "2026-01-01 00:00:00",
        "2026-03-29 00:30:00",
        "2026-03-29 02:00:00",
        "2026-08-31 23:30:00",
    ]))
    utc = _irish_local_to_utc(local)
    assert utc.tolist() == pd.to_datetime([
        "2026-01-01 00:00:00",
        "2026-03-29 00:30:00",
        "2026-03-29 01:00:00",
        "2026-08-31 22:30:00",
    ]).tolist()

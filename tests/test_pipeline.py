from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_canonical import build
from backend.app.proxy import add_pressure_proxy
from backend.app.optimizer import FlexibleAsset, optimize_absorption



def test_proxy_bounds_with_simple_frame():
    df = pd.DataFrame({
        "renewable_vre_share": [0.1, 0.5, 0.9],
        "residual_load_mw": [900, 500, 100],
        "sem_price_currency_per_mwh": [200, 100, 50],
    })
    out = add_pressure_proxy(df)
    assert out["pressure_proxy"].between(0, 1).all()
    assert out["pressure_proxy"].iloc[-1] > out["pressure_proxy"].iloc[0]


def test_optimizer_never_exceeds_available_surplus():
    assets = [FlexibleAsset("EV fleet", 10.0, 20.0, [True, True, True, True])]
    result = optimize_absorption([4, 5, 0, 8], assets)
    sched = result["schedule_mw"]["EV fleet"]
    assert all(x <= s + 1e-8 for x, s in zip(sched, [4, 5, 0, 8]))

from scripts.import_dispatch_down import normalize_sheet
from scripts.enrich_training_table import merge as merge_training


def test_dispatch_down_reason_categories_are_aggregated():
    df = pd.DataFrame({
        "Date Time": ["01/01/2026 00:00", "01/01/2026 00:30"],
        "Jurisdiction": ["IE", "IE"],
        "Fuel": ["Wind", "Wind"],
        "SNSP Issue (MWh)": [2.0, 0.0],
        "ROCOF / Inertia (MWh)": [1.0, 0.5],
        "High Freq / Min Gen (MWh)": [3.0, 4.0],
        "Transmission (TSO) Constraints (MWh)": [5.0, 6.0],
        "TSO Testing (MWh)": [0.2, 0.0],
    })
    out = normalize_sheet(df, "Wind")
    assert out["curtailment_mwh"].tolist() == [6.0, 4.5]
    assert out["constraint_mwh"].tolist() == [5.2, 6.0]
    assert out["tso_testing_mwh"].tolist() == [0.2, 0.0]
    assert out["dispatch_down_total_mwh"].tolist() == [11.2, 10.5]


def test_training_join_preserves_canonical_rows(tmp_path):
    base = pd.DataFrame({"timestamp": ["2026-01-01 00:00:00", "2026-01-01 00:30:00"], "load_mw": [1, 2]})
    ctx = pd.DataFrame({"timestamp": ["2026-01-01 00:00:00"], "snsp_pct": [70]})
    labels = pd.DataFrame({"timestamp": ["2026-01-01 00:30:00"], "dispatch_down_total_mwh": [3.5]})
    bp, cp, lp = tmp_path / "b.csv", tmp_path / "c.csv", tmp_path / "l.csv"
    base.to_csv(bp, index=False); ctx.to_csv(cp, index=False); labels.to_csv(lp, index=False)
    out = merge_training(bp, cp, lp)
    assert len(out) == 2
    assert out.loc[0, "snsp_pct"] == 70
    assert out.loc[1, "dispatch_down_total_mwh"] == 3.5

from scripts.import_dispatch_down import normalize_official_dd_hh


def test_official_dd_schema_uses_excel_serial_and_does_not_double_count_testing():
    # 46023.0 = 2026-01-01 00:00 in Excel's 1900 date system.
    df = pd.DataFrame({
        "UT_TYPE": ["Wind"],
        "JURISDICTION": ["IE"],
        "HH_TIMESTAMP": [46023.0],
        "GMT_OFFSET": [0],
        "Sum of AV_MWH": [100.0],
        "Sum of AO_MWH": [80.0],
        "Sum of HI_FRQ_MIN_GEN_MWH": [3.0],
        "Sum of ROCOF_INERTIA_MWH": [2.0],
        "Sum of SNSP_MWH": [5.0],
        "Sum of TRANS_CONSTR_MWH": [7.0],
        "Sum of TSO_TEST_MWH": [1.0],
        "Sum of DD_MWH": [18.0],
        "Sum of CURTAILMENTS_MWH": [10.0],
        "Sum of CONSTRAINTS_MWH": [8.0],
        "Sum of OTHER_MWH": [0.0],
    })
    out = normalize_official_dd_hh(df)
    assert str(out.iloc[0]["timestamp"]) == "2026-01-01 00:00:00"
    assert out.iloc[0]["dispatch_down_total_mwh"] == 18.0
    assert out.iloc[0]["constraint_mwh"] == 8.0
    assert out.iloc[0]["curtailment_mwh"] == 10.0
    assert abs(out.iloc[0]["dd_formula_error_mwh"]) < 1e-9

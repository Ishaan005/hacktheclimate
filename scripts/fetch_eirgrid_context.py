from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

UA = "hack-the-climate-team-blue/0.1 (+public research; contact in repo)"

VARGEN_URL = "https://www.vargen.smartgriddashboard.com/api/export/{start}/{end}/{region}/{area}"
INTERCONN_URL = "https://www.interconn.smartgriddashboard.com/api/Interconnector/{start}/{end}/ALL"
DASHBOARD_URL = "https://www.smartgriddashboard.com/DashboardService.svc/data"


def _get_json(url: str, *, params: dict[str, str] | None = None, attempts: int = 6) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=45, headers={"User-Agent": UA})
            r.raise_for_status()
            payload = r.json()
            if not isinstance(payload, dict) or "Rows" not in payload:
                raise ValueError(f"Unexpected response shape from {r.url}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last = exc
            if attempt + 1 == attempts:
                break
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def _month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = start + pd.offsets.MonthBegin(1)
    return start, end


def _path_ts(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y%m%d%H%M")


def _dashboard_date(ts: pd.Timestamp) -> str:
    return ts.strftime("%d-%b-%Y")


def _rows(payload: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(payload.get("Rows", []))


def fetch_month(year: int, month: int, raw_dir: Path) -> pd.DataFrame:
    start, end_exclusive = _month_bounds(year, month)
    end_inclusive = end_exclusive - pd.Timedelta(minutes=1)
    raw_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []

    # Wind/solar actual + forecast (15-min), Republic of Ireland.
    for area in ("WIND", "SOLAR"):
        url = VARGEN_URL.format(
            start=_path_ts(start), end=_path_ts(end_inclusive), region="ROI", area=area
        )
        payload = _get_json(url, params={"FORMAT": "JSON"})
        (raw_dir / f"{area.lower()}_roi_{year}_{month:02d}.json").write_text(json.dumps(payload))
        df = _rows(payload)
        if not df.empty:
            ts_col = "Effective_Date" if "Effective_Date" in df.columns else "EffectiveTime"
            df["timestamp"] = pd.to_datetime(df[ts_col], dayfirst=True, errors="coerce")
            value_col = "Value"
            name_col = "FieldName"
            wide = df.pivot_table(index="timestamp", columns=name_col, values=value_col, aggfunc="mean")
            wide.columns = [str(c).lower() for c in wide.columns]
            rename = {}
            if area == "WIND":
                rename.update({
                    "wind_actual": "eirgrid_wind_actual_mw",
                    "wind_fcast": "eirgrid_wind_forecast_mw",
                    "mw_actual": "eirgrid_wind_actual_mw",
                    "mw_forecast": "eirgrid_wind_forecast_mw",
                })
            else:
                rename.update({
                    "solar_actual": "eirgrid_solar_actual_mw",
                    "solar_fcast": "eirgrid_solar_forecast_mw",
                    "mw_actual": "eirgrid_solar_actual_mw",
                    "mw_forecast": "eirgrid_solar_forecast_mw",
                })
            wide = wide.rename(columns=rename)
            frames.append(wide)

    # All-island interconnector feed includes EWIC, Greenlink, Moyle and Net.
    url = INTERCONN_URL.format(start=_path_ts(start), end=_path_ts(end_inclusive))
    payload = _get_json(url, params={"format": "json"})
    (raw_dir / f"interconnection_all_{year}_{month:02d}.json").write_text(json.dumps(payload))
    df = _rows(payload)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["Effective_Date"], dayfirst=True, errors="coerce")
        wide = df.pivot_table(index="timestamp", columns="Field_Name", values="Value", aggfunc="mean")
        wide = wide.rename(columns={
            "INTER_EWIC": "interconnector_ewic_mw",
            "INTER_GRNLK": "interconnector_greenlink_mw",
            "INTER_MOYLE": "interconnector_moyle_mw",
            "INTER_NET": "interconnector_net_all_island_mw",
        })
        # Smart Grid Dashboard convention documented by the upstream API: positive = import.
        if {"interconnector_ewic_mw", "interconnector_greenlink_mw"}.issubset(wide.columns):
            wide["interconnector_net_ie_mw"] = wide["interconnector_ewic_mw"] + wide["interconnector_greenlink_mw"]
        frames.append(wide)

    # Dashboard system variables. These are independent calls because supported regions differ.
    dashboard_specs = [
        ("demandActual", "ROI", "eirgrid_demand_actual_mw"),
        ("SnspAll", "ALL", "snsp_pct"),
        ("co2Emission", "ROI", "co2_emission_t_per_h"),
    ]
    for area, region, out_name in dashboard_specs:
        payload = _get_json(
            DASHBOARD_URL,
            params={
                "area": area,
                "region": region,
                "datefrom": _dashboard_date(start),
                "dateto": _dashboard_date(end_exclusive),
            },
        )
        (raw_dir / f"{area.lower()}_{region.lower()}_{year}_{month:02d}.json").write_text(json.dumps(payload))
        df = _rows(payload)
        if not df.empty:
            ts_col = "EffectiveTime" if "EffectiveTime" in df.columns else "Effective_Date"
            df["timestamp"] = pd.to_datetime(df[ts_col], dayfirst=True, errors="coerce")
            value_col = "Value"
            one = df.groupby("timestamp", as_index=True)[value_col].mean().rename(out_name).to_frame()
            frames.append(one)

    if not frames:
        raise RuntimeError("No EirGrid context data returned.")

    merged = pd.concat(frames, axis=1).sort_index()
    # Canonical training data are 30-minute. Average 15-min point measurements within each half-hour.
    merged = merged.resample("30min").mean()
    merged.index.name = "timestamp"
    return merged.reset_index()


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch official EirGrid system/context data for one month.")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--month", type=int, required=True, choices=range(1, 13))
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw/eirgrid"))
    p.add_argument("--output", type=Path, default=Path("data/processed/eirgrid_context.csv"))
    args = p.parse_args()

    out = fetch_month(args.year, args.month, args.raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"wrote {len(out):,} half-hour rows -> {args.output}")
    print(out.notna().mean().sort_values().rename("coverage").to_string())


if __name__ == "__main__":
    main()

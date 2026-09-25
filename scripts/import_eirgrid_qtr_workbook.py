from __future__ import annotations

import argparse
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
EXCEL_ORIGIN = datetime(1899, 12, 30)

SOURCE_TO_OUTPUT = {
    "NI Demand": "eirgrid_ni_demand_mw",
    "NI Wind Availability": "eirgrid_ni_wind_availability_mw",
    "NI Wind Generation": "eirgrid_ni_wind_generation_mw",
    "NI Solar Availability": "eirgrid_ni_solar_availability_mw",
    "NI Solar Generation": "eirgrid_ni_solar_generation_mw",
    "NI Batteries": "eirgrid_ni_batteries_mw",
    "Moyle I/C": "eirgrid_moyle_ic_mw",
    "IE Generation": "eirgrid_ie_generation_mw",
    "IE Demand": "eirgrid_ie_demand_mw",
    "IE Wind Availability": "eirgrid_ie_wind_availability_mw",
    "IE Wind Generation": "eirgrid_ie_wind_generation_mw",
    "IE Solar Availability": "eirgrid_ie_solar_availability_mw",
    "IE Solar Generation": "eirgrid_ie_solar_generation_mw",
    "IE Hydro": "eirgrid_ie_hydro_mw",
    "EWIC I/C": "eirgrid_ewic_ic_mw",
    "Greenlink I/C": "eirgrid_greenlink_ic_mw",
    "IE Wind Penetration": "eirgrid_ie_wind_penetration_pct",
    "IE Solar Penetration": "eirgrid_ie_solar_penetration_pct",
    "AI Generation": "eirgrid_ai_generation_mw",
    "AI Demand": "eirgrid_ai_demand_mw",
    "AI Wind Availability": "eirgrid_ai_wind_availability_mw",
    "AI Wind Generation": "eirgrid_ai_wind_generation_mw",
    "AI Solar Availability": "eirgrid_ai_solar_availability_mw",
    "AI Solar Generation": "eirgrid_ai_solar_generation_mw",
    "AI Hydro": "eirgrid_ai_hydro_mw",
    "Inter-Jurisdictional Flow": "eirgrid_interjurisdictional_flow_mw",
    "AI Wind Penetration": "eirgrid_ai_wind_penetration_pct",
    "AI Solar Penetration": "eirgrid_ai_solar_penetration_pct",
    "AI Oversupply": "eirgrid_ai_oversupply_mw",
    "AI Oversupply Percentage": "eirgrid_ai_oversupply_pct",
    "SNSP": "eirgrid_snsp_pct",
}
PERCENT_FIELDS = {
    "IE Wind Penetration", "IE Solar Penetration", "AI Wind Penetration",
    "AI Solar Penetration", "AI Oversupply Percentage", "SNSP",
}


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [
        "".join((t.text or "") for t in si.iter(f"{{{NS_MAIN}}}t"))
        for si in root.findall(f"{{{NS_MAIN}}}si")
    ]


def _col_num(ref: str) -> int:
    m = re.match(r"([A-Z]+)", ref)
    if not m:
        raise ValueError(f"Bad cell reference: {ref}")
    n = 0
    for ch in m.group(1):
        n = n * 26 + ord(ch) - 64
    return n


def _iter_system_rows(path: Path):
    """Stream the first worksheet from the official workbook without loading 8MB into memory."""
    with zipfile.ZipFile(path) as z:
        strings = _shared_strings(z)
        with z.open("xl/worksheets/sheet1.xml") as f:
            for _, elem in ET.iterparse(f, events=("end",)):
                if elem.tag != f"{{{NS_MAIN}}}row":
                    continue
                values: dict[int, object] = {}
                for c in elem.findall(f"{{{NS_MAIN}}}c"):
                    idx = _col_num(c.attrib["r"]) - 1
                    typ = c.attrib.get("t")
                    v = c.find(f"{{{NS_MAIN}}}v")
                    inline = c.find(f"{{{NS_MAIN}}}is")
                    if typ == "s" and v is not None:
                        value = strings[int(v.text)]
                    elif typ == "inlineStr" and inline is not None:
                        value = "".join((t.text or "") for t in inline.iter(f"{{{NS_MAIN}}}t"))
                    elif v is not None:
                        value = v.text
                    else:
                        value = None
                    values[idx] = value
                yield values
                elem.clear()


def load_context(path: Path, year: int, month: int) -> pd.DataFrame:
    rows = _iter_system_rows(path)
    header_row = next(rows)
    headers = [header_row.get(i) for i in range(max(header_row) + 1)]
    header_index = {h: i for i, h in enumerate(headers) if h}

    missing = (set(SOURCE_TO_OUTPUT) | {"DateTime"}) - set(header_index)
    if missing:
        raise ValueError(f"Unexpected EirGrid workbook schema; missing: {sorted(missing)}")

    groups: dict[pd.Timestamp, list[dict[int, object]]] = defaultdict(list)
    for values in rows:
        raw = values.get(header_index["DateTime"])
        if raw in (None, ""):
            continue
        try:
            ts = pd.Timestamp(EXCEL_ORIGIN + timedelta(days=float(raw)))
        except (TypeError, ValueError):
            continue
        if ts.year != year or ts.month != month:
            continue
        half_hour = ts.floor("30min")
        groups[half_hour].append(values)

    output: list[dict[str, object]] = []
    for ts in sorted(groups):
        source_rows = groups[ts]
        row: dict[str, object] = {"timestamp": ts, "eirgrid_qtr_points": len(source_rows)}
        for source, dest in SOURCE_TO_OUTPUT.items():
            idx = header_index[source]
            nums: list[float] = []
            for values in source_rows:
                raw = values.get(idx)
                if raw not in (None, ""):
                    try:
                        nums.append(float(raw))
                    except (TypeError, ValueError):
                        pass
            value = sum(nums) / len(nums) if nums else float("nan")
            if source in PERCENT_FIELDS:
                value *= 100.0
            row[dest] = value

        row["eirgrid_ie_vre_actual_mw"] = row["eirgrid_ie_wind_generation_mw"] + row["eirgrid_ie_solar_generation_mw"]
        row["eirgrid_ie_vre_available_mw"] = row["eirgrid_ie_wind_availability_mw"] + row["eirgrid_ie_solar_availability_mw"]
        row["eirgrid_ie_wind_availability_gap_mw"] = max(row["eirgrid_ie_wind_availability_mw"] - row["eirgrid_ie_wind_generation_mw"], 0.0)
        row["eirgrid_ie_solar_availability_gap_mw"] = max(row["eirgrid_ie_solar_availability_mw"] - row["eirgrid_ie_solar_generation_mw"], 0.0)
        row["eirgrid_ie_vre_availability_gap_proxy_mw"] = row["eirgrid_ie_wind_availability_gap_mw"] + row["eirgrid_ie_solar_availability_gap_mw"]
        row["eirgrid_ie_gb_interconnector_net_mw"] = row["eirgrid_ewic_ic_mw"] + row["eirgrid_greenlink_ic_mw"]
        output.append(row)

    out = pd.DataFrame(output).sort_values("timestamp")
    if out.empty:
        raise ValueError(f"No rows found for {year}-{month:02d}")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Import EirGrid System Data Qtr Hourly workbook and aggregate to 30 minutes.")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--year", required=True, type=int)
    p.add_argument("--month", required=True, type=int, choices=range(1, 13))
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    out = load_context(args.input, args.year, args.month)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"wrote {len(out):,} half-hour rows -> {args.output}")
    print(out.notna().mean().rename("coverage").sort_values().to_string())


if __name__ == "__main__":
    main()

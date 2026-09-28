"""Build a forecast-vintage-preserving Irish GFS point panel for daily 06Z decisions.

The upstream NOAA GFS forecasts are read through dynamical.org's public point
API. Responses are cached under ignored data/raw/ so interrupted runs resume.
Each day's f030 NOAA GRIB object timestamp is checked before its forecast is
accepted as available for the 06Z decision. No global GRIB files are fetched.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests


API = "https://api.dynamical.org/v1/forecasts"
PRODUCT = "noaa-gfs-forecast"
VARS = ["wind_u_100m", "wind_v_100m", "temperature_2m", "downward_short_wave_radiation_flux_surface"]
UNITS = {"wind_u_100m": "m s-1", "wind_v_100m": "m s-1", "temperature_2m": "degree_Celsius", "downward_short_wave_radiation_flux_surface": "W m-2"}
SITES = {
    "donegal": (54.65, -8.10),
    "mayo": (53.85, -9.30),
    "kerry": (52.20, -9.80),
    "cork": (51.90, -8.50),
    "dublin": (53.35, -6.26),
}


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_url(issue: datetime) -> str:
    return ("https://noaa-gfs-bdp-pds.s3.amazonaws.com/"
            f"gfs.{issue:%Y%m%d}/00/atmos/gfs.t00z.pgrb2.0p25.f030")


def request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    for attempt in range(6):
        try:
            response = requests.request(method, url, timeout=120, **kwargs)
            if response.status_code not in (429, 500, 502, 503, 504):
                response.raise_for_status()
                return response
            wait = min(60, int(response.headers.get("Retry-After", 2 ** attempt)))
        except (requests.Timeout, requests.ConnectionError):
            wait = min(60, 2 ** attempt)
        if attempt == 5:
            break
        time.sleep(wait)
    raise RuntimeError(f"Upstream unavailable after retries: {method} {url}")


def fetch_day(issue: datetime, cache_dir: Path) -> Path:
    path = cache_dir / f"{issue:%Y%m%d}_00.json"
    if path.exists():
        return path
    head = request_with_retry("HEAD", source_url(issue))
    last_modified = parsedate_to_datetime(head.headers["Last-Modified"]).astimezone(timezone.utc)
    decision = issue + timedelta(hours=6)
    if last_modified > decision:
        raise ValueError(f"NOAA f030 object arrived after decision: {issue} {last_modified}")
    queries = [
        {
            "dataProductId": PRODUCT,
            "queryId": site,
            "location": {"latitude": lat, "longitude": lon},
            "initTime": iso(issue),
            "maxLeadTimeHours": 30,
            "variables": VARS,
        }
        for site, (lat, lon) in SITES.items()
    ]
    response = request_with_retry("POST", API, json={"queries": queries})
    payload = {
        "issue_time": iso(issue),
        "retrieved_at_utc": iso(datetime.now(timezone.utc)),
        "noaa_f030_url": source_url(issue),
        "noaa_f030_last_modified_utc": iso(last_modified),
        "noaa_f030_etag": head.headers.get("ETag"),
        "api_url": API,
        "api_sha256": hashlib.sha256(response.content).hexdigest(),
        "response": response.json(),
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload))
    temporary.replace(path)
    return path


def normalize(cache_paths: list[Path]) -> tuple[pd.DataFrame, dict]:
    records: dict[tuple[str, int], dict] = {}
    manifest_days = []
    selected_points: dict[str, dict] = {}
    snapshots = set()
    for path in sorted(cache_paths):
        payload = json.loads(path.read_text())
        issue = utc(payload["issue_time"])
        if utc(payload["noaa_f030_last_modified_utc"]) > issue + timedelta(hours=6):
            raise ValueError(f"Late source object in {path}")
        results = payload["response"]["results"]
        if {r["queryId"] for r in results} != set(SITES):
            raise ValueError(f"Missing or unexpected site in {path}")
        day_meta = {key: payload[key] for key in ("issue_time", "retrieved_at_utc", "noaa_f030_url", "noaa_f030_last_modified_utc", "noaa_f030_etag", "api_sha256")}
        day_meta["site_sources"] = {}
        for result in results:
            site = result["queryId"]
            if result["dataProduct"]["id"] != PRODUCT:
                raise ValueError(f"Wrong product in {path}")
            selected_points[site] = result["point"]
            snapshots.add(result["snapshotId"])
            if {name: meta["unit"] for name, meta in result["variables"].items()} != UNITS:
                raise ValueError(f"Unexpected GFS units in {path}")
            forecasts = result["forecasts"]
            if len(forecasts) != 1 or utc(forecasts[0]["initTime"]) != issue:
                raise ValueError(f"Wrong issue in {path}")
            forecast = forecasts[0]
            canonical = forecast["links"]["canonical"]
            day_meta["site_sources"][site] = f"https://api.dynamical.org{canonical}" if canonical.startswith("/") else canonical
            for index, lead in enumerate(forecast["leadTimeHours"]):
                lead = int(lead)
                if lead < 6 or lead > 30:
                    continue
                valid = utc(forecast["validTimes"][index])
                if valid != issue + timedelta(hours=lead):
                    raise ValueError(f"Wrong valid time in {path}")
                key = (payload["issue_time"], lead)
                row = records.setdefault(key, {
                    "issue_time_utc": payload["issue_time"],
                    "decision_time_utc": iso(issue + timedelta(hours=6)),
                    "valid_time_utc": iso(valid),
                    "lead_hours": lead,
                    "source_available_at_utc": payload["noaa_f030_last_modified_utc"],
                    "source_snapshot_id": result["snapshotId"],
                })
                for variable in VARS:
                    values = forecast["data"][variable]
                    if len(values) != len(forecast["leadTimeHours"]) or values[index] is None:
                        raise ValueError(f"Missing {variable} at {site} {valid}")
                    row[f"{site}_{variable}"] = float(values[index])
                row[f"{site}_wind_speed_100m"] = float(np.hypot(row[f"{site}_wind_u_100m"], row[f"{site}_wind_v_100m"]))
        manifest_days.append(day_meta)
    frame = pd.DataFrame(records.values()).sort_values(["issue_time_utc", "lead_hours"]).reset_index(drop=True)
    expected_cols = {f"{site}_{name}" for site in SITES for name in (*VARS, "wind_speed_100m")}
    if not expected_cols.issubset(frame.columns) or frame[list(expected_cols)].isna().any().any():
        raise ValueError("Incomplete site features")
    speed_cols = [f"{site}_wind_speed_100m" for site in SITES]
    frame["mean_wind_speed_100m"] = frame[speed_cols].mean(axis=1)
    frame["west_wind_speed_100m"] = frame[[f"{site}_wind_speed_100m" for site in ("donegal", "mayo", "kerry")]].mean(axis=1)
    frame["south_wind_speed_100m"] = frame[[f"{site}_wind_speed_100m" for site in ("kerry", "cork")]].mean(axis=1)
    frame["mean_temperature_2m_c"] = frame[[f"{site}_temperature_2m" for site in SITES]].mean(axis=1)
    frame["mean_solar_w_m2"] = frame[[f"{site}_downward_short_wave_radiation_flux_surface" for site in SITES]].mean(axis=1)
    manifest = {
        "provider": "NOAA GFS forecasts processed by dynamical.org",
        "product": PRODUCT,
        "source_catalog": "https://dynamical.org/catalog/noaa-gfs-forecast/",
        "license": "CC-BY-4.0",
        "decision_rule": "00Z issue, 06Z decision; source f030 Last-Modified must be no later than decision",
        "point_selection": selected_points,
        "units": UNITS,
        "snapshot_ids": sorted(snapshots),
        "days": manifest_days,
    }
    return frame, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2026-01-01")
    parser.add_argument("--end", default="2026-09-01", help="Exclusive UTC issue date")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/gfs_daily"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug_manifest.json"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    issues = [timestamp.to_pydatetime() for timestamp in pd.date_range(args.start, args.end, freq="D", inclusive="left", tz="UTC")]
    paths = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_day, issue, args.cache_dir): issue for issue in issues}
        for future in as_completed(futures):
            paths.append(future.result())
            if len(paths) % 10 == 0 or len(paths) == len(issues):
                print(f"Fetched or resumed {len(paths)}/{len(issues)} days", flush=True)
    frame, manifest = normalize(paths)
    if len(frame) != len(issues) * 25:
        raise ValueError(f"Expected {len(issues) * 25} issue/lead rows; got {len(frame)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    args.manifest.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(frame)} rows to {args.output} and provenance to {args.manifest}")


if __name__ == "__main__":
    main()

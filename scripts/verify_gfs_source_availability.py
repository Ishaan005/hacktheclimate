"""Verify every NOAA GFS GRIB forecast hour used by the daily model.

Checks S3 object Last-Modified for hours 6-30 of each 00Z run. This catches
cycles in which f030 is not the last object to arrive. The resulting latest
timestamp replaces the f030 proxy in the processed point panel.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path

import pandas as pd
if __package__:
    from .fetch_gfs_daily_panel import request_with_retry
else:
    from fetch_gfs_daily_panel import request_with_retry


def inspect_one(issue_date: str, cache_dir: Path) -> Path:
    path = cache_dir / f"{issue_date}.json"
    if path.exists():
        return path
    issue = datetime.strptime(issue_date, "%Y%m%d").replace(tzinfo=timezone.utc)
    base = f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{issue_date}/00/atmos/gfs.t00z.pgrb2.0p25"

    def check_lead(lead: int) -> dict:
        url = f"{base}.f{lead:03d}"
        response = request_with_retry("HEAD", url)
        modified = parsedate_to_datetime(response.headers["Last-Modified"]).astimezone(timezone.utc)
        return {"lead_hours": lead, "url": url, "last_modified_utc": modified.isoformat().replace("+00:00", "Z"),
                "etag": response.headers.get("ETag")}

    with ThreadPoolExecutor(max_workers=2) as executor:
        leads = sorted(executor.map(check_lead, range(6, 31)), key=lambda row: row["lead_hours"])
    latest = max(leads, key=lambda row: row["last_modified_utc"])
    payload = {
        "issue_time_utc": issue.isoformat().replace("+00:00", "Z"),
        "decision_time_utc": (issue + timedelta(hours=6)).isoformat().replace("+00:00", "Z"),
        "source_available_at_utc": latest["last_modified_utc"],
        "latest_lead_hours": latest["lead_hours"],
        "lead_objects": leads,
    }
    if datetime.fromisoformat(latest["last_modified_utc"].replace("Z", "+00:00")) > issue + timedelta(hours=6):
        raise ValueError(f"GFS forecast not fully available by 06Z: {issue_date} {latest}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload))
    temporary.replace(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug.csv"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/gfs_release_checks"))
    parser.add_argument("--release-manifest", type=Path, default=Path("data/processed/gfs_daily_2026_jan_aug_release_manifest.json"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    panel = pd.read_csv(args.panel)
    issues = sorted(pd.to_datetime(panel.issue_time_utc, utc=True).dt.strftime("%Y%m%d").unique())
    paths = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(inspect_one, date, args.cache_dir): date for date in issues}
        for future in as_completed(futures):
            paths.append(future.result())
            if len(paths) % 20 == 0 or len(paths) == len(issues):
                print(f"Verified all 25 forecast hours for {len(paths)}/{len(issues)} days", flush=True)
    days = [json.loads(path.read_text()) for path in sorted(paths)]
    availability = {day["issue_time_utc"]: day["source_available_at_utc"] for day in days}
    if len(availability) != len(issues):
        raise ValueError("Missing or duplicate release check")
    panel["source_available_at_utc"] = panel.issue_time_utc.map(availability)
    if panel.source_available_at_utc.isna().any():
        raise ValueError("No release check for some panel rows")
    decision = pd.to_datetime(panel.decision_time_utc, utc=True)
    available = pd.to_datetime(panel.source_available_at_utc, utc=True)
    if (available > decision).any():
        raise ValueError("Late GFS source in panel")
    panel.to_csv(args.panel, index=False)
    args.release_manifest.write_text(json.dumps({
        "source": "NOAA GFS 0.25 degree S3 GRIB objects, forecast hours 6-30",
        "interpretation": "S3 object Last-Modified is an availability proxy, not a provider SLA or ingestion log",
        "decision_rule": "All 25 lead objects must exist by issue time plus six hours",
        "days": days,
    }, indent=2))
    margins = (decision - available).dt.total_seconds() / 3600
    print(f"Updated {args.panel}; minimum availability margin {margins.min():.2f} hours")


if __name__ == "__main__":
    main()

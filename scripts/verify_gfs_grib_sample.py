"""Compare the local 25 January NOAA GRIB sample with the processed GFS panel.

Requires the ignored sample directory containing 100u.grib2, 100v.grib2,
dswrf.grib2 and manifest.json, plus the optional ``eccodes`` Python package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

try:
    import eccodes
except ImportError as exc:
    raise SystemExit("Install optional eccodes to verify the raw GRIB sample") from exc


EXPECTED = {
    "100u.grib2": ("u", "heightAboveGround", 100, "m s**-1", "wind_u_100m"),
    "100v.grib2": ("v", "heightAboveGround", 100, "m s**-1", "wind_v_100m"),
    "dswrf.grib2": ("sdswrf", "surface", 0, "W m**-2", "downward_short_wave_radiation_flux_surface"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", required=True, type=Path)
    parser.add_argument("--panel", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.sample_dir / "manifest.json").read_text())
    panel = pd.read_csv(args.panel)
    row = panel[(panel.issue_time_utc == "2026-01-24T00:00:00Z") & panel.lead_hours.eq(24)]
    if len(row) != 1:
        raise ValueError("Exactly one January 24 issue at lead 24 is required")
    row = row.iloc[0]
    points = pd.read_csv(args.sample_dir / "irish_points_sample.csv")
    for field in manifest["fields"]:
        file = field["file"]
        expected = EXPECTED[file]
        path = args.sample_dir / file
        if hashlib.sha256(path.read_bytes()).hexdigest() != field["sha256"]:
            raise ValueError(f"Checksum mismatch: {file}")
        with path.open("rb") as stream:
            handle = eccodes.codes_grib_new_from_file(stream)
            try:
                actual = tuple(eccodes.codes_get(handle, key) for key in ("shortName", "typeOfLevel", "level", "units"))
                if actual != expected[:4]:
                    raise ValueError(f"Wrong field/level/units in {file}: {actual}")
                if (eccodes.codes_get(handle, "dataDate"), eccodes.codes_get(handle, "dataTime"),
                    eccodes.codes_get(handle, "step"), eccodes.codes_get(handle, "validityDate"),
                    eccodes.codes_get(handle, "validityTime")) != (20260124, 0, 24, 20260125, 0):
                    raise ValueError(f"Wrong issue or valid time in {file}")
                for point in points.itertuples():
                    site = point.location.lower()
                    decoded = eccodes.codes_grib_find_nearest(handle, point.requested_lat, point.requested_lon, False, 1)[0]["value"]
                    processed = float(row[f"{site}_{expected[4]}"])
                    if abs(decoded - processed) > 0.1:
                        raise ValueError(f"Decoded/API mismatch at {site} {file}: {decoded} vs {processed}")
            finally:
                eccodes.codes_release(handle)
        print(f"Verified {file}: checksum, field, units, times and five Irish points")


if __name__ == "__main__":
    main()

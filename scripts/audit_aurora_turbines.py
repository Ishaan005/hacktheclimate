"""Read-only audit of local Aurora forecasts and the Irish turbine inventory.

This deliberately does not train a model or write a derived weather archive.
The source directory is supplied explicitly because its access terms and
provenance must be checked before it becomes part of the project data pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def inspect_stream(directory: Path) -> dict:
    files = sorted(directory.glob("*.nc"))
    if not files:
        raise ValueError(f"No complete NetCDF files in {directory}")

    issues = []
    missing_leads = {}
    dimensions = set()
    units = set()
    bbox = set()
    value_ranges = {name: [float("inf"), float("-inf")] for name in ("wind_speed", "temperature")}
    nonfinite_values = {name: 0 for name in value_ranges}
    for path in files:
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            issue = pd.Timestamp(ds.attrs["issue_time"])
            leads = ds.lead_time.values.astype(int)
            absent = sorted(set(range(int(leads.max()) + 1)) - set(leads))
            if absent:
                missing_leads[path.name] = absent
            expected = (issue.tz_convert(None).to_datetime64() + leads.astype("timedelta64[h]"))
            if not np.array_equal(ds.valid_time.values, expected):
                raise ValueError(f"Valid times do not match issue + lead: {path}")
            if int(ds.attrs["completed_count"]) != len(leads):
                raise ValueError(f"Completed count does not match leads: {path}")
            issues.append(issue)
            dimensions.add(tuple((name, int(size)) for name, size in ds.sizes.items()))
            units.add((ds.wind_speed.attrs.get("units"), ds.wind_speed.attrs.get("long_name"),
                       ds.temperature.attrs.get("units"), ds.temperature.attrs.get("long_name")))
            bbox.add(tuple(float(ds.attrs[f"bbox_{side}"]) for side in ("west", "south", "east", "north")))
            for name in value_ranges:
                values = ds[name].values
                finite = np.isfinite(values)
                nonfinite_values[name] += int((~finite).sum())
                if finite.any():
                    value_ranges[name][0] = min(value_ranges[name][0], float(values[finite].min()))
                    value_ranges[name][1] = max(value_ranges[name][1], float(values[finite].max()))

    interval = pd.Timedelta(hours=6 if directory.name == "oper" else 12)
    expected_issues = pd.date_range(min(issues), max(issues), freq=interval)
    return {
        "files": len(files),
        "first_issue_utc": str(min(issues)),
        "last_issue_utc": str(max(issues)),
        "missing_cycles": [str(t) for t in expected_issues.difference(pd.DatetimeIndex(issues))],
        "missing_leads": missing_leads,
        "dimensions": [dict(d) for d in sorted(dimensions)],
        "variable_metadata": [dict(zip(("wind_units", "wind_name", "temperature_units", "temperature_name"), u)) for u in sorted(units)],
        "bounding_boxes": [list(b) for b in sorted(bbox)],
        "value_ranges": value_ranges,
        "nonfinite_values": nonfinite_values,
        "incomplete_downloads": [p.name for p in sorted(directory.glob("*.part"))],
    }


def inspect_turbines(path: Path) -> tuple[dict, pd.DataFrame]:
    farms = pd.read_csv(path)
    required = {"Latitude", "Longitude", "Total power", "Number of turbines"}
    if set(farms.columns) != required:
        raise ValueError(f"Unexpected turbine columns: {list(farms.columns)}")
    located = farms.dropna(subset=["Latitude", "Longitude"]).drop_duplicates().copy()
    if (located["Total power"] <= 0).any():
        raise ValueError("Turbine weights must be positive")
    return {
        "rows": len(farms),
        "geolocated_rows": int(farms[["Latitude", "Longitude"]].notna().all(axis=1).sum()),
        "missing_coordinates": int(farms[["Latitude", "Longitude"]].isna().any(axis=1).sum()),
        "missing_turbine_counts": int(farms["Number of turbines"].isna().sum()),
        "exact_duplicate_rows": int(farms.duplicated().sum()),
        "distinct_coordinates": int(farms.dropna(subset=["Latitude", "Longitude"])[["Latitude", "Longitude"]].drop_duplicates().shape[0]),
        "raw_total_power": float(farms["Total power"].sum()),
        "geolocated_deduplicated_power": float(located["Total power"].sum()),
        "power_unit": "unverified",
    }, located


def sample_operational_wind(directory: Path, farms: pd.DataFrame, labels: pd.DataFrame) -> dict:
    """Compare same-valid-hour wind indices with measured Irish wind generation.

    Each six-hour issue contributes leads 6-11 and 24-29, giving unique valid
    hours per lead band. Issue time is a model cycle, not proof of release time.
    """
    records = []
    distance_km = None
    cell_count = None
    for path in sorted(directory.glob("*.nc")):
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            lat = ds.latitude.values
            lon = ds.longitude.values
            if not (farms.Latitude.between(lat.min(), lat.max()).all() and
                    farms.Longitude.between(lon.min(), lon.max()).all()):
                raise ValueError(f"Turbine coordinate outside Aurora grid: {path}")
            lat_idx = np.abs(lat[:, None] - farms.Latitude.to_numpy()[None, :]).argmin(axis=0)
            lon_idx = np.abs(lon[:, None] - farms.Longitude.to_numpy()[None, :]).argmin(axis=0)
            if distance_km is None:
                a = np.sin(np.deg2rad(lat[lat_idx] - farms.Latitude.to_numpy()) / 2) ** 2
                a += np.cos(np.deg2rad(farms.Latitude.to_numpy())) * np.cos(np.deg2rad(lat[lat_idx])) * np.sin(np.deg2rad(lon[lon_idx] - farms.Longitude.to_numpy()) / 2) ** 2
                distance_km = 2 * 6371 * np.arcsin(np.sqrt(a))
                cell_count = len(set(zip(lat_idx, lon_idx)))
            weights = farms["Total power"].to_numpy(dtype=float)
            for first_lead in (6, 24):
                selector = np.where((ds.lead_time.values >= first_lead) & (ds.lead_time.values < first_lead + 6))[0]
                wind_grid = ds.wind_speed.isel(lead_time=selector).values
                wind = wind_grid[:, lat_idx, lon_idx]
                if not np.isfinite(wind).all():
                    raise ValueError(f"Nonfinite sampled wind in {path}")
                for row, valid in enumerate(ds.valid_time.values[selector]):
                    records.append({
                        "valid_time": pd.Timestamp(valid),
                        "lead_band_hours": first_lead,
                        "weighted_wind_10m_mps": float(np.average(wind[row], weights=weights)),
                        "weighted_wind_cubed": float(np.average(wind[row] ** 3, weights=weights)),
                        "equal_farm_wind_10m_mps": float(np.mean(wind[row])),
                        "equal_farm_wind_cubed": float(np.mean(wind[row] ** 3)),
                        "bbox_grid_wind_10m_mps": float(np.mean(wind_grid[row])),
                        "bbox_grid_wind_cubed": float(np.mean(wind_grid[row] ** 3)),
                    })
    frame = pd.DataFrame(records)
    if frame.duplicated(["valid_time", "lead_band_hours"]).any():
        raise ValueError("Overlapping issue windows produced duplicate valid hours")
    joined = frame.merge(labels, left_on="valid_time", right_on="timestamp", how="inner", validate="one_to_one" if len(frame.lead_band_hours.unique()) == 1 else "many_to_one")
    result = {
        "nearest_grid_cell_count": cell_count,
        "nearest_cell_distance_km_median": float(np.median(distance_km)),
        "nearest_cell_distance_km_max": float(np.max(distance_km)),
        "lead_bands": {},
    }
    for band, group in joined.groupby("lead_band_hours"):
        result["lead_bands"][str(band)] = {
            "matched_hourly_labels": len(group),
            "first_valid_time": str(group.valid_time.min()),
            "last_valid_time": str(group.valid_time.max()),
            "wind_speed_vs_measured_generation_pearson": float(group.weighted_wind_10m_mps.corr(group.eirgrid_ie_wind_generation_mw)),
            "wind_cubed_vs_measured_generation_pearson": float(group.weighted_wind_cubed.corr(group.eirgrid_ie_wind_generation_mw)),
            "equal_farm_wind_vs_measured_generation_pearson": float(group.equal_farm_wind_10m_mps.corr(group.eirgrid_ie_wind_generation_mw)),
            "equal_farm_wind_cubed_vs_measured_generation_pearson": float(group.equal_farm_wind_cubed.corr(group.eirgrid_ie_wind_generation_mw)),
            "bbox_grid_wind_vs_measured_generation_pearson": float(group.bbox_grid_wind_10m_mps.corr(group.eirgrid_ie_wind_generation_mw)),
            "bbox_grid_wind_cubed_vs_measured_generation_pearson": float(group.bbox_grid_wind_cubed.corr(group.eirgrid_ie_wind_generation_mw)),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aurora-root", required=True, type=Path)
    parser.add_argument("--turbines", type=Path, default=Path("data/processed/ie_turbines.csv"))
    parser.add_argument("--labels", type=Path, default=Path("data/processed/training_table_eirgrid_2026_jan_aug.csv"))
    args = parser.parse_args()
    turbine_audit, farms = inspect_turbines(args.turbines)
    labels = pd.read_csv(args.labels, usecols=["timestamp", "eirgrid_ie_wind_generation_mw"], parse_dates=["timestamp"])
    result = {
        "aurora": {stream: inspect_stream(args.aurora_root / stream) for stream in ("oper", "enfo")},
        "turbines": turbine_audit,
        "operational_wind_feasibility": sample_operational_wind(args.aurora_root / "oper", farms, labels),
        "interpretation": "Same-valid-time descriptive check only; provider publication times, turbine source rights, and installed-capacity status remain unverified.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

# Aurora and Irish turbine data audit

Checked locally on 28 September 2026. This is a source feasibility study, not a trained model or a day-ahead performance result.

## Files inspected

- Aurora NetCDF directory: `../Aurora_Temperature_Wind_BBox` in the original local workspace. The files are **not** committed to this repository.
- Turbine table: [`data/processed/ie_turbines.csv`](../data/processed/ie_turbines.csv).
- Same-time comparison data: [`data/processed/training_table_eirgrid_2026_jan_aug.csv`](../data/processed/training_table_eirgrid_2026_jan_aug.csv), using its measured Irish wind generation column.

The NetCDF attributes identify collection `mai-aurora` and `oper`/`enfo` streams. The file metadata does **not** establish the download endpoint, terms, publication time, or whether this is the Aurora 1.5 Foundry model described in [Microsoft's model catalog](https://ai.azure.com/catalog/models/Aurora-1.5?publisher=microsoft). Keep those separate until the export method is supplied.

| Source | What is present | Quality and scope |
| --- | --- | --- |
| Aurora `oper` | 30 six-hourly issue cycles, 1–8 May 2026; 373 hourly leads (0–372) per file | Complete issue sequence and lead grids. Each file has 23 latitudes × 25 longitudes across 51–56.5°N, 11–5°W. |
| Aurora `enfo` | 10 twelve-hourly issue cycles, 1–5 May 2026; 24 members and up to 301 hourly leads | Two complete files omit 7 lead hours in total. A further 6 May file has only a `.part` download and is excluded. |
| Irish turbines | 329 rows; latitude, longitude, `Total power`, turbine count | 323 geolocated rows, 6 without coordinates, 28 without turbine counts, 8 exact duplicate rows. 247 distinct coordinate pairs. |

Both Aurora streams store **10 m wind speed in m/s** and **2 m air temperature in K**. The documented Aurora 1.5 model can expose 100 m wind, but these files do not contain it. Do not use the 10 m values as hub-height wind or convert them to turbine output with an unvalidated power curve. The turbine file gives no farm names, IDs, operating status, commissioning dates, or grid bus IDs. Its raw `Total power` sums to 5,310,915; the unit is absent from the file. The schema resembles [The Wind Power's Irish tables](https://www.thewindpower.net/country_zones_en_18_ireland.php), which label power in kW, but the provided CSV's claimed WindEurope provenance and its unit still need confirmation from the original export.

Every complete NetCDF file has internally consistent issue, lead, and valid times. The audit found no nonfinite wind or temperature values. Across all cells, operational wind ranges from 0.002 to 24.18 m/s and temperature from 270.70 to 294.66 K; ensemble values range from 0.0004 to 28.61 m/s and 267.04 to 298.45 K. These are file checks, not independent forecast verification.

## Small wind-signal check

For each operational issue, the audit sampled 10 m wind at the nearest grid cell for each geolocated, exact-deduplicated turbine row. It compared six-hour blocks at lead hours 6–11 and 24–29 to measured Irish wind generation at the same valid hours. Power values were used only as **relative weights**, so no unit conversion was assumed. All 315 retained rows fall within the bounding box; they sample 98 distinct grid cells, with median nearest-cell distance 9.6 km and maximum 15.7 km.

| Issue-to-valid lead band | Matched hours | Pearson correlation: power-weighted mean wind / measured generation | Equal-site mean wind | Whole-box mean wind |
| --- | ---: | ---: | ---: | ---: |
| 6–11 h | 180 | 0.845 | 0.837 | 0.778 |
| 24–29 h | 180 | 0.861 | 0.862 | 0.877 |

A power-weighted mean of cubed wind has correlations 0.829 and 0.894 for the two bands; equal-site cubed wind is 0.817 and 0.894. The capacity weights do not clearly improve the longer-lead signal over equal-site weighting in this short sample. This comparison tests whether the weather field contains a plausible national wind signal. It does **not** test dispatch-down forecasting, calibration, location-specific output, or network constraints. The hours are serially correlated, and no confidence interval or out-of-period holdout is claimed.

## What the sources can support

1. **Exploratory national wind feature:** nearest-grid or area-aggregated 10 m wind, with explicit issue/valid times, can be compared with measured wind and later used as a candidate forecast covariate if usage rights and release timing are confirmed.
2. **Spatial sampling:** the turbine coordinates can select relevant Aurora cells. The power weights remain provisional until the source, units, duplicates, and 2026 operating status are verified.
3. **Ensemble research:** 24 members are available for short-window spread and uncertainty experiments after resolving missing leads and the incomplete download.

The sources do **not** supply 100 m hub-height wind, a validated MW forecast, bus-level generator allocation, demand forecasts, or a direct constraint/curtailment target. They therefore cannot fill the required regional MW or action inputs in the [network forecast adapter](NETWORK_FORECAST_ARCHITECTURE.md) on their own.

## Gates before model training or operational use

- Obtain the original Aurora export script/page, retrieval timestamps or release-lag evidence, and terms allowing forecast retention and model training. `issue_time` is the model cycle; it is not proof that the file was available to an operator at that instant.
- Obtain the original turbine export/page and license. Confirm whether the source is WindEurope or another provider, the `Total power` unit, whether rows include planned or retired assets, and why coordinates repeat. Do not publish a cleaned derivative or assume 5.31 GW of operating capacity from this file.
- Collect a much longer archive, preferably with multiple seasons, and preserve when each forecast became available. The current May window is suitable for pipeline validation, not a robust chronological day-ahead backtest.
- Join each future weather value to a decision time only after its actual release time, then compare a forecast-safe weather model against calendar and lag baselines on later held-out dates. Map hourly weather explicitly to the half-hour dispatch-down target without inventing 30-minute weather resolution.
- Resolve site-to-grid-bus identities and operating status separately before using these rows for a location-specific network scenario.

## Reproduce the read-only audit

Install the optional packages with `python -m pip install -r requirements-weather-audit.txt`, then run from the repository root:

```bash
python scripts/audit_aurora_turbines.py \
  --aurora-root /absolute/path/to/Aurora_Temperature_Wind_BBox
```

The script prints JSON. It reads the existing NetCDF, turbine CSV, and measured generation table and writes no weather extract or trained artifact. It excludes `.part` files automatically and fails if valid times do not equal issue time plus lead or if sampled wind is nonfinite.

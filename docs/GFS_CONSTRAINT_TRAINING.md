# National constraint forecast training with archived GFS

Checked on 28 September 2026 against [Ground Truth #5](https://github.com/Ishaan005/hacktheclimate/issues/5) and the [forecast data](https://github.com/Ishaan005/hacktheclimate/issues/6), [baseline](https://github.com/Ishaan005/hacktheclimate/issues/7) and [backtest](https://github.com/Ishaan005/hacktheclimate/issues/8) issues. This is a hackathon research model, not a validated operating forecast.

## Data and decision contract

The weather panel contains 243 daily **00Z NOAA GFS runs** from 1 January through 31 August 2026. The source is [NOAA GFS](https://registry.opendata.aws/noaa-gfs-bdp-pds/), accessed as a point forecast through [dynamical.org's GFS archive and API](https://dynamical.org/catalog/noaa-gfs-forecast/) under CC BY 4.0. Attribution: *NOAA NWS NCEP GFS data processed by dynamical.org from NOAA Open Data Dissemination archives.* The five points (Donegal, Mayo, Kerry, Cork and Dublin) match the local NOAA pilot. Their 100 m U/V wind, 2 m temperature and surface shortwave radiation forecasts are stored with the model run, valid hour, source snapshot and units in [`gfs_daily_2026_jan_aug.csv`](../data/processed/gfs_daily_2026_jan_aug.csv). The [point-source manifest](../data/processed/gfs_daily_2026_jan_aug_manifest.json) records canonical point URLs, selected grid cells and API response checksums. The [release manifest](../data/processed/gfs_daily_2026_jan_aug_release_manifest.json) records the NOAA S3 URL, ETag and `Last-Modified` time for **every** forecast-hour GRIB object used. Raw API responses and GRIB files remain under ignored `data/raw/`.

Every forecast decision is fixed at **06:00 UTC**, six hours after its 00Z GFS run. All 25 forecast-hour objects used for that day's decision must have a `Last-Modified` time no later than 06:00; the panel stores the **latest** of those timestamps. The narrowest observed margin is **4 minutes 50 seconds**. The full panel has 6,075 issue/valid-hour rows (leads 6–30), with no missing days or values. The independent 24 January f024 GRIB sample was decoded with ecCodes and matched to the API panel at all five points for 100 m U/V wind and surface solar radiation, including checksum, field, units, issue and valid time. The source object's timestamp is stronger evidence than assuming zero publication delay, but it is still **an S3 availability proxy**, not a published provider SLA or a live ingestion log.

| Issue month | Daily cycles | Hourly leads per point | Missing points, leads or values | Duplicate issue/valid pairs |
| --- | ---: | ---: | ---: | ---: |
| January | 31 | 775 | 0 | 0 |
| February | 28 | 700 | 0 | 0 |
| March | 31 | 775 | 0 | 0 |
| April | 30 | 750 | 0 | 0 |
| May | 31 | 775 | 0 | 0 |
| June | 30 | 750 | 0 | 0 |
| July | 31 | 775 | 0 | 0 |
| August | 31 | 775 | 0 | 0 |

Each of the five points has this coverage. There are 242 repeated **valid** hours across adjacent daily cycles, at 06:00 the next day; their issue times differ. Forecast rows are keyed by both issue and valid time, and each target half-hour is assigned to one decision only. The January f024 sample has a valid time of 25 January 00:00, the date of the existing ground-truth label example.

Each 06:00 decision has 48 targets from 06:30 through 06:00 the next day. The hourly weather forecast at or before each target time is used for both half-hours; this does not create 30-minute weather resolution. Joining to official EirGrid labels produces **11,649 unique target half-hours** through 31 August. The first 13 January label intervals precede the first decision; the final daily forecast extends beyond the label end at 22:30 on 31 August. The [training table](../data/processed/gfs_constraint_training_2026_jan_aug.csv) retains source availability, model issue, decision, weather valid time, target time and horizon. Checks reject a source released after decision, a future weather issuance, duplicate target, missing forecast hour, or overlapping train/calibration/test periods.

The target is **national `constraint_mwh`**, with material event defined provisionally as `constraint_mwh > 5 MWh` in a half-hour. `curtailment_mwh` remains a separate label and is never merged into the target. Same-period or lagged EirGrid measurements and official dispatch-down labels are **not predictors**: their publication delays have not been established for this historical dataset. This is why the forecast-safe reference is calendar-only, rather than the calendar-plus-grid-lags requested in issue #7. The prior grid-lag model's timestamp-correct but availability-uncertain results should not be treated as a like-for-like operational baseline.

The supplied May Aurora archive is only eight days of issue cycles and contains 10 m wind; the `ie_turbines.csv` export lacks confirmed source rights and operating-status metadata. Neither is used to fit this January–August model. They remain useful for the separate spatial sampling audit and a later weather-source comparison.

## Model and evaluation

The model shares training across all 0.5–24 hour horizons, with horizon and future calendar features plus GFS weather at the target hour. A gradient-boosting classifier predicts the event; a separate positive-event regressor estimates conditional constraint MWh; their product is reported as expected MWh. The calendar reference uses the same two-part algorithm without weather. Previous-month calibration uses isotonic regression for event probability and absolute-residual intervals for nominal 80% and 90% MWh ranges. These ranges have measured historical coverage, not guaranteed future coverage.

The backtest uses expanding training, the immediately preceding month for calibration, and a separate test month from April through August. The final candidate artifact is trained through July and calibrated on August; it has **not** been evaluated on September or a live event.

| Test month | Intervals | Event prevalence | GFS PR-AUC | Calendar PR-AUC | GFS MAE (MWh) | Calendar MAE | Zero MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| April | 1,440 | 0.485 | 0.921 | 0.525 | 57.2 | 93.8 | 79.7 |
| May | 1,488 | 0.536 | 0.873 | 0.567 | 62.2 | 89.1 | 82.3 |
| June | 1,440 | 0.619 | 0.901 | 0.625 | 70.0 | 83.2 | 84.2 |
| July | 1,488 | 0.568 | 0.928 | 0.778 | 31.3 | 95.4 | 55.4 |
| August | 1,486 | 0.292 | 0.684 | 0.529 | **17.4** | 60.4 | **15.0** |

Across all 7,342 held-out intervals, GFS PR-AUC is **0.870** versus **0.618** for calendar, and expected-MWh MAE is **47.4** versus **84.3** for calendar and **63.1** for zero. The nominal 80% and 90% intervals cover 84.6% and 92.3% overall. Coverage and calibration are uneven by month: May event expected-calibration error is 0.253, May 90% interval coverage is 87.3%, and June 80% coverage is 78.7%. August has a large prevalence shift and the GFS expected-MWh forecast fails to beat zero MAE. It should not be presented as an established day-ahead volume improvement across every month.

For **exactly 24 hours ahead**, the combined April–August sample is only 153 target intervals, one per daily decision. Its PR-AUC is 0.827 and MAE is 31.6 MWh, versus calendar 70.0 and zero 41.0. In August alone the exact-24h model MAE is 8.3 versus zero 7.5 on 31 intervals. The full model nonetheless emits every half-hour through 24 hours; the small exact-horizon subset should not be read as a high-precision operational estimate.

These are national labels. They do not identify a constrained bus, line or farm, do not forecast curtailment, and do not measure energy that an action could avoid. Five points are a sparse representation of Irish weather. Revisit point selection and source timing before connecting the model to the network scenario or action ranking.

## Reproduce and use the saved candidate

Run from the repository root in the Python environment from the main README:

```bash
python scripts/fetch_gfs_daily_panel.py --start 2026-01-01 --end 2026-09-01
python scripts/verify_gfs_source_availability.py
python scripts/train_gfs_constraint.py
python scripts/predict_gfs_constraint.py \
  --weather data/processed/gfs_daily_2026_jan_aug.csv \
  --issue-date 2026-08-31 --output .cache/gfs_constraint_smoke.csv
```

Both the fetch and release check are resumable through ignored `data/raw/` caches. Training requires the complete release manifest. A fresh source audit can compare the local January raw GRIB sample, if present, with the processed panel:

```bash
python -m pip install -r requirements-gfs-validation.txt
python scripts/verify_gfs_grib_sample.py \
  --sample-dir /absolute/path/to/noaa_gfs_sample_20260124_00z_step24 \
  --panel data/processed/gfs_daily_2026_jan_aug.csv
```

The saved [metrics](../artifacts/gfs_constraint/metrics.json), [held-out predictions](../artifacts/gfs_constraint/backtest_predictions.csv), [August evaluation model](../artifacts/gfs_constraint/heldout_august_model.joblib) and [final candidate model](../artifacts/gfs_constraint/final_model.joblib) are separate from the January retrospective demo and the earlier grid-lag artifacts. Use the final model only with a new source-checked daily GFS panel and its release manifest. Pass a nondefault manifest with `--release-manifest` when forecasting a new issue. Preserve issue, decision and snapshot IDs with every prediction.

## Remaining ground-truth gates

- Confirm the production retrieval and publication SLA; an S3 `Last-Modified` timestamp does not measure every downstream delay.
- Obtain a documented historical availability rule for EirGrid actuals before adding demand, wind or constraint lags to the baseline or weather model.
- Review the provisional `>5 MWh` material-event threshold with an operator; it creates about 50% event prevalence in the backtest.
- Evaluate later months and live shadow-mode forecasts, especially low-prevalence regimes like August, and recalibrate or reject the model when it fails simple baselines.
- Keep national forecast confidence separate from network and action confidence. Location-specific and avoided-energy claims require reviewed asset mapping, physical network checks and action availability.

# Model plan

## 1. Separate nowcast and forecast products

### Nowcast / operator dashboard
May use current actual load, actual wind/solar, current market signals and measured grid variables. It can describe present dispatch-down pressure.

### Day-ahead forecast
Must only use information available before the prediction horizon. Same-period actual generation/load are leakage. Use historical lags plus forecasts/future-known values.

## 2. Real target

Preferred half-hour target:

- `dispatch_down_total_mwh`
- decomposed into `constraint_mwh` and `curtailment_mwh`
- keep `reason_code` / `constraint_group` when source data supports them

For a 30-minute period, `MWh = MW * 0.5` when the MW value is an interval average.

## 3. Baseline architecture

Use a hurdle/two-stage model:

1. Classifier: will dispatch-down occur in this interval?
2. Regressor: conditional on occurrence, what MWh will be dispatched down?

A histogram gradient-boosting baseline is included because it works well on tabular nonlinear data and handles missing feature values.

## 4. Forecast-safe feature candidates

- Hour/day/week cyclic encodings; weekend/holiday flags.
- Historical load lags: 1h, 2h, 24h, 7d.
- Historical wind lags: 1h, 2h, 24h, 7d.
- Historical price lags and rolling statistics.
- Wind/load ramps.
- Future weather forecasts: wind speed/direction at hub-height proxies, temperature, irradiance/cloud cover.
- Future wind and demand forecasts when supplied by EirGrid/organisers.
- Confirmed day-ahead SEM price if its publication semantics are verified.
- Interconnector flow/availability and outage indicators when available.
- Constraint group / regional grid features for local constraints.

## 5. Evaluation

Never random split the time series for final reporting. Use chronological backtests / rolling-origin validation.

Report separately:

- occurrence PR-AUC (and precision/recall at operational thresholds)
- MWh MAE for volume
- weighted MWh error during the highest-risk periods
- product metric: MWh successfully absorbable by the optimiser under the predicted schedule

## 6. Until labels arrive

`pressure_proxy` exists only so the dashboard/API can be built now. It combines high VRE share, low residual load and low price. Do not call it a probability, model prediction or curtailment estimate.

## 7. Features now available from the official 2026 quarter-hourly workbook

For a **nowcast/operator** model, the January table now includes measured IE/all-island demand and generation, wind/solar availability and output, SNSP, EWIC/Greenlink/Moyle flow, inter-jurisdictional flow, hydro, NI batteries, and all-island oversupply.

For a **forecast** model, do not feed same-period actual values directly. Convert these into historical lags/rolling statistics, and replace contemporaneous actuals with point-in-time forecasts where available.

The most promising physical feature families to test once DD labels arrive are:

1. SNSP level and recent trajectory.
2. Wind/solar availability and historical ramps.
3. Demand level and demand ramps.
4. EWIC/Greenlink/Moyle and inter-jurisdictional flow, preserving the source sign convention.
5. SEM price / negative or low-price regimes.
6. All-island oversupply estimate.
7. Calendar/seasonal features.
8. Network/constraint-group features if the DD workbook exposes location or reason detail.

Do **not** train or report accuracy against the availability-gap proxy. Use it only for exploratory plots and plumbing until the real DD half-hourly MWh labels are present.

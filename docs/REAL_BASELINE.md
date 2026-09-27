# Real-label baseline model

This is a **hackathon baseline**, not a production-performance claim.

## Event definition

For the demo classifier, a material dispatch-down event is:

`dispatch_down_total_mwh > 5`

The continuous target remains the official `dispatch_down_total_mwh`.

## Chronological holdout

Initial smoke-test split:

- Train: 1–23 January 2026
- Test: 24–31 January 2026

### Same-period operational nowcast

Uses contemporaneous system state (demand, wind/solar availability and output, SNSP, interconnectors, price, oversupply) plus calendar features.

- PR-AUC: **0.982**
- ROC-AUC: **0.952**
- Precision @ 0.5: **0.986**
- Recall @ 0.5: **0.736**
- Expected-volume MAE: **36.2 MWh**
- Zero-prediction MAE on the same test period: **67.7 MWh**

### 1-hour-ahead operational forecast

Uses measured system state at time `t` to predict official dispatch-down at `t + 1 hour`, with recent 1-hour deltas and target-time calendar features.
The chronological split is applied to the **target timestamp** so no training label falls inside the holdout period.

- PR-AUC: **0.983**
- ROC-AUC: **0.952**
- Precision @ 0.5: **0.986**
- Recall @ 0.5: **0.747**
- Expected-volume MAE: **41.1 MWh**
- Zero-prediction MAE on the same test period: **67.7 MWh**

## Critical caveat

January has strong regime shifts: the final-week test set contains many more material events than some earlier January windows. These headline numbers are therefore only proof that the signal is learnable, **not** a credible final accuracy claim.

An expanding-window monthly backtest on matching January–August system context is now included in [`artifacts/rolling_1h/metrics.json`](../artifacts/rolling_1h/metrics.json). April–August event PR-AUC ranges from **0.897 to 0.975**, with August event prevalence at **0.307** versus **0.535–0.632** in the other four folds. Expected-volume MAE ranges from **19.8 to 57.6 MWh**, below the corresponding zero-prediction MAE in each fold. Reproduce it with `python scripts/backtest_1h_operational.py --output .cache/rolling-check.json`. This remains retrospective: operational publication latency is unknown, and it does not validate a day-ahead product.

Also keep these products separate:

1. **Nowcast/operator tool:** contemporaneous actual system measurements are allowed.
2. **Forecast:** only measurements available before the target horizon plus true future-known forecasts/market information are allowed.

The trained smoke-test artifacts and metrics live under `artifacts/real_baseline/`.

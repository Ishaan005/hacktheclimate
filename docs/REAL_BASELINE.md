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

- PR-AUC: **0.983**
- ROC-AUC: **0.951**
- Precision @ 0.5: **0.981**
- Recall @ 0.5: **0.749**
- Expected-volume MAE: **41.1 MWh**
- Zero-prediction MAE on the same test period: **67.8 MWh**

## Critical caveat

January has strong regime shifts: the final-week test set contains many more material events than some earlier January windows. These headline numbers are therefore only proof that the signal is learnable, **not** a credible final accuracy claim.

Before presenting model performance to judges, run rolling multi-month / rolling-origin validation once matching system-context data for more months is available. Report fold-by-fold event prevalence alongside PR-AUC because PR-AUC changes substantially with prevalence.

Also keep these products separate:

1. **Nowcast/operator tool:** contemporaneous actual system measurements are allowed.
2. **Forecast:** only measurements available before the target horizon plus true future-known forecasts/market information are allowed.

The trained smoke-test artifacts and metrics live under `artifacts/real_baseline/`.

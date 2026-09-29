# GFS model readiness and freeze

Checked on 29 September 2026. The canonical forward path is **one 00Z NOAA GFS issue, a 06:00 UTC decision, and 48 half-hour national forecasts through the next 06:00**. The served model is `artifacts/gfs_constraint/final_model.joblib`; its source and model hashes are recorded in `artifacts/gfs_model_readiness.json` and each live inference snapshot. Earlier grid-lag models remain research artifacts because historical publication timing for their EirGrid inputs has not been established.

## Decision

| Output | Gate | Evidence |
| --- | --- | --- |
| National constraint event probability | **Demo/shadow ready, experimental** | Forecast-safe GFS features; April–August chronological folds; event PR-AUC beats calendar in every month and pooled (0.870 vs 0.618). |
| Expected constraint MWh and 80%/90% ranges | **Experimental** | Pooled MAE 47.4 MWh vs zero 63.1, but August MAE 17.4 vs zero 15.0. Historical interval coverage is measured, not guaranteed. |
| National curtailment event probability | **Research result** | The same GFS/calendar pipeline beats calendar PR-AUC in all five months; pooled 0.517 vs 0.270. Material event threshold remains provisional. |
| Expected curtailment MWh | **Unavailable for live use** | Pooled MAE 53.7 MWh vs zero 49.9; it also loses to zero in May (47.5 vs 23.5) and August (32.1 vs 24.6). |
| Total dispatch-down MWh | **Unavailable** | Both components need defensible volume forecasts. Do not add the two candidate outputs or present a partial sum as total. |
| Locational risk, action or avoided MWh | **Unvalidated** | National weather and labels do not identify a constrained line or prove an intervention. |

The curtailment experiment uses the **same** forecast-safe features, `>5 MWh` provisional event definition, expanding April–August backtest, previous-month calibration, and two-part classifier/positive-volume regressor as constraint. It is saved separately under `artifacts/gfs_curtailment/`; its training table retains both distinct official labels. Neither target uses contemporaneous or lagged EirGrid actuals as predictors. A poor volume result is a model gate, not a reason to tune repeatedly against August.

## Reproduce the gates

Use Python 3.11 from the repository root:

```bash
python scripts/train_gfs_constraint.py --target constraint_mwh
python scripts/train_gfs_constraint.py --target curtailment_mwh
python -m scripts.check_gfs_model_readiness
```

The audit verifies source and saved-artifact hashes, the all-lead NOAA release manifest, source timing, feature allowlist, unique targets, chronological folds, and held-out metrics recomputed from saved predictions. It writes `artifacts/gfs_model_readiness.json`. Its default required gate is `constraint_event`; use `--require curtailment` or `--require total` in a release gate to get a nonzero exit while those outputs remain unsupported. `--snapshot /path/to/latest.json --require live` additionally checks that a published inference snapshot is current and has future intervals. Absence of a snapshot is **unavailable**, not zero.

Model acceptance is intentionally narrow: source and chronology checks must pass, event PR-AUC must beat the calendar model in each held-out month and pooled, and calibration/interval coverage must have been measured. Volume promotion also requires MAE below zero in every month and pooled. This is a hackathon demo gate, not production approval. The `>5 MWh` event definition, source availability proxy, future regime shifts and post-August labelled holdout remain open evidence needs. Keep the August failures visible and collect new shadow results before reconsidering any volume gate.

The live `GET /v1/forecast/constraint` path accepts only a checked constraint artifact. It emits future national constraint rows with probability, expected MWh, historical ranges, model hash/version and GFS issue/source times. Its status and limitations identify the volume as experimental. The network and operator routes have separate input, safety and action gates; passing this model audit does not promote them.

In the API schema, `target_time_utc` is the valid time, `event_probability` is constraint probability, `expected_constraint_mwh` is expected volume, and `lower_80_mwh`/`upper_80_mwh` and `lower_90_mwh`/`upper_90_mwh` are the measured uncertainty ranges. `model.artifact_sha256` identifies the exact fit and `issue_time_utc` identifies the weather cycle. `status: experimental` describes confidence in this research output; there is no calibrated single-number `forecast_confidence` score.

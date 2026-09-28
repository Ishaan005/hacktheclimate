# Verified state and remaining work

Checked locally on 27 September 2026, before the hackathon. This is a historical snapshot, not the current feature inventory or a performance or impact claim. See the [GFS training report](GFS_CONSTRAINT_TRAINING.md) and [inference runbook](GFS_INFERENCE.md) for work completed afterward.

## What runs

- Python 3.11 environment installs with no broken requirements; all automated tests pass.
- The organiser CSVs, January EirGrid workbook context, six DD workbooks, and January labeled table rebuild from the original local sources. Rebuilt values and coverage match the included files.
- The EirGrid system workbook converts Irish local time to UTC. Its January–August context has **11,662 unique half-hours**, and every one matches an official 2026 DD label in [`training_table_eirgrid_2026_jan_aug.csv`](../data/processed/training_table_eirgrid_2026_jan_aug.csv).
- The January baseline retrains and its saved artifacts load. The API serves health and both historical sample routes at their 336-row limit, representing source gaps as JSON `null`.
- An expanding-window backtest trains on all prior labeled months and evaluates April, May, June, July, and August 2026 separately. The five folds have event PR-AUC **0.897–0.975**; each fold's prevalence and error baselines are in [`artifacts/rolling_1h/metrics.json`](../artifacts/rolling_1h/metrics.json). This is retrospective evaluation of a 1-hour operational model, not day-ahead validation.
- `POST /v1/demo/absorption` replays January held-out model predictions into the flexible-load optimiser and returns an illustrative schedule, along with source/target times and observed dispatch-down for comparison.
- A local Docker image packages the API and the small subset of data/model files it needs. The container and a preview-first Azure Container Apps handoff are documented in [`AZURE_HANDOFF.md`](AZURE_HANDOFF.md); no cloud deployment or paid weather calls have been made for this preparation.
- The optional Smart Grid Dashboard fetcher returns 1,488 January half-hours after respecting the upstream 30-day range limit. Its CO₂ series has about 95% coverage, so it is exploratory; the versioned workbook remains the baseline source.

## What is still missing for the product

1. **A point-in-time day-ahead forecast.** The current 1-hour baseline uses measured system state at time `t`. Weather and other forecasts available at the actual issue time are not integrated. Publication delays for operational measurements also need checking.
2. **Evaluation of the intervention target.** The five monthly folds validate total dispatch-down prediction retrospectively, but separate constraint and curtailment targets, calibration, and a comparison against historical/forecast-only inputs remain. PR-AUC varies with each fold's event prevalence.
3. **Measured intervention impact.** The demo assumes all predicted total dispatch-down MWh are locally absorbable, which is an unvalidated upper bound. It does not establish flexible-load location, actual demand response, or avoided dispatch-down. A judged impact claim needs site/network feasibility and a counterfactual or controlled measurement.
4. **Day-ahead inputs and event record.** A short May 2026 `mai-aurora` forecast archive is now available locally; see the [source audit](AURORA_TURBINE_DATA_AUDIT.md). Its release times, usage rights, and 10 m wind suitability remain unresolved, and it is not integrated into a validated day-ahead model. Obtain a longer point-in-time forecast archive and check operational data publication latency. The repo is now on GitHub for teammates; record the final pre-event commit SHA and timestamp in [`PREEXISTING.md`](../PREEXISTING.md) at the event boundary.

See the [model plan](MODEL_PLAN.md) for feature boundaries and the [data guide](DATA_GUIDE.md) for source and output files.

Repeat the monthly evaluation with `python scripts/backtest_1h_operational.py --output .cache/rolling-check.json`.

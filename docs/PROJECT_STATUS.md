# Verified state and remaining work

Checked locally on 26 September 2026, before the hackathon. This is a prototype status, not a performance or impact claim.

## What runs

- Python 3.11 environment installs with no broken requirements; all automated tests pass.
- The organiser CSVs, January EirGrid workbook context, six DD workbooks, and January labeled table rebuild from the original local sources. Rebuilt values and coverage match the included files.
- The EirGrid system workbook converts Irish local time to UTC. Its January–August context has **11,662 unique half-hours**, and every one matches an official 2026 DD label in [`training_table_eirgrid_2026_jan_aug.csv`](../data/processed/training_table_eirgrid_2026_jan_aug.csv).
- The January baseline retrains and its saved artifacts load. The API serves health and both historical sample routes at their 336-row limit, representing source gaps as JSON `null`.
- The optional Smart Grid Dashboard fetcher returns 1,488 January half-hours after respecting the upstream 30-day range limit. Its CO₂ series has about 95% coverage, so it is exploratory; the versioned workbook remains the baseline source.

## What is still missing for the product

1. **A point-in-time day-ahead forecast.** The current 1-hour baseline uses measured system state at time `t`. Weather and other forecasts available at the actual issue time are not integrated. Publication delays for operational measurements also need checking.
2. **Reliable evaluation across regimes.** The saved models use a January-only split. A temporary January–June train / July–August test on the included multi-month table produced 1-hour event PR-AUC about **0.935** and expected-volume MAE about **26.0 MWh**. This is one retrospective holdout, not rolling validation or a final accuracy claim. Fold-level prevalence and separate constraint/curtailment targets remain to be evaluated.
3. **An end-to-end intervention demo.** `optimize_absorption` runs, but it takes supplied surplus MW; no route or UI connects a forecast to a flexible-load schedule and measured avoided dispatch-down MWh.
4. **Team distribution and event record.** This local Git repo has no remote. The final pre-event commit SHA and timestamp in [`PREEXISTING.md`](../PREEXISTING.md) must be recorded at the event boundary. Review data redistribution terms before making a public repo; the current handoff assumes a private team repo.

See the [model plan](MODEL_PLAN.md) for feature boundaries and the [data guide](DATA_GUIDE.md) for source and output files.

The multi-month holdout can be repeated with `python scripts/train_real_baseline.py --input data/processed/training_table_eirgrid_2026_jan_aug.csv --split 2026-07-01 --output-dir .cache/jul-aug-check`.

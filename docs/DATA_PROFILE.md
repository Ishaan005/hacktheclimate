# Organiser sample data profile

Analysed from the three supplied files on 25 September 2026.

## Coverage

- `generation.csv`: 19,468 rows, 4 source columns; 1 Jan–31 Jan 2026; map codes `IE` and `GB`.
- `load.csv`: 2,955 rows, 3 source columns; same date range; map codes `IE` and `GB`.
- `prices.csv`: 2,232 rows, 4 source columns; same date range; map codes `IE_SEM` and `GB`.
- Generation/load timestamps are 30-minute periods. `IE_SEM` prices are hourly; GB prices are 30-minute.

## Ireland quality findings

- Irish generation has 1,482 timestamps: 6 complete half-hours are absent across all nine listed Irish production types.
- Irish load has 1,466 timestamps: 22 half-hours are missing.
- `Solar` is present but is **0 MW for every Irish row in this January sample**.
- `Fossil Hard coal` is also 0 MW throughout the Irish sample.
- Summed listed generation does not balance to load (mean shortfall about 1.27 GW on rows where both are present), so do **not** interpret the production categories as a complete system supply stack. Imports and/or other sources are not represented in these samples.
- The files contain no dispatch-down, constraint, curtailment, availability, or reason-code label.

## Price caveats

- The organiser column is `Price[Currency/MWh]`, not `EUR/MWh`; do not subtract IE and GB prices until currency semantics are confirmed.
- IE `UpdateTime(UTC)` generally looks like a publication time before delivery, but a repeated daily edge case means the timestamp should not be used naively as a feature.
- GB update timestamps are mostly after the delivery interval and include one large anomaly. Exclude `UpdateTime(UTC)` from modelling until source semantics are confirmed.

## Descriptive relationship in the sample

For complete Ireland rows, wind+solar share is inversely associated with SEM price (Pearson correlation about -0.58). That is useful as an exploratory market-pressure signal, but **not** a dispatch-down ground truth.

# Pre-existing work log

This repository scaffold was prepared before the event coding period.

Record the pre-hackathon Git commit SHA here immediately before the event starts:

- Commit SHA: `TODO`
- Timestamp: `TODO`
- Prepared components: data ingestion, validation, canonical schema, feature scaffolding, pressure proxy, optimiser skeleton, API skeleton, tests.

Any competition-day work should be committed after this marker so it is easy to distinguish pre-existing infrastructure from hackathon development.

## 2026-09-25 EirGrid enrichment added before the event

The following were added before the 28 September hackathon start:
- official Smart Grid Dashboard system/interconnector downloader
- half-hourly EirGrid dispatch-down workbook normalizer
- canonical/context/label joiner
- source/sign-convention/leakage documentation
- tests for reason-code aggregation and timestamp joins

## 25 Sep 2026 — official EirGrid workbook integration

Before the hackathon, the repository was extended to import the official 2026 quarter-hourly system workbook, aggregate it to 30 minutes, retain Ireland/all-island renewable and interconnector context, and produce a merged January context table. Availability-gap fields are explicitly documented as weak diagnostics rather than authoritative dispatch-down labels.

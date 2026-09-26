# EirGrid enrichment sources

## Official quarter-hourly workbook (preferred for the hackathon)

Use EirGrid's `System Data Qtr Hourly` workbook when available. The inspected 2026 V8 workbook contains 15-minute average SCADA data for 1 Jan through 31 Aug 2026. The importer aggregates pairs of 15-minute averages to the canonical 30-minute grid.

The workbook `DateTime` is Irish local clock time. The importer converts aggregated half-hours to UTC before a join with DD labels, including the March daylight-saving change. The January data are unchanged by this conversion.

Retained system context includes Ireland, Northern Ireland and all-island demand/generation; wind and solar availability/output; hydro; EWIC, Greenlink and Moyle interconnector flow; inter-jurisdictional flow; SNSP; renewable penetration; and EirGrid's all-island oversupply estimate.

### Flow sign convention

The workbook's numeric interconnector signs are preserved exactly. Do not relabel positive/negative as import/export in model-facing features unless the operational sign convention has been confirmed from EirGrid documentation or an expert at the event. `eirgrid_ie_gb_interconnector_net_mw` is simply EWIC + Greenlink under the source convention.

## Smart Grid API fallback

`scripts/fetch_eirgrid_context.py` remains an optional live-data route using the public Smart Grid Dashboard backends. For reproducible hackathon training, prefer the versioned workbook above.

## Dispatch-down labels

The **DD Half-Hourly Data** publication is a separate source from the system workbook. The system workbook's wind/solar availability-minus-output gap and all-island oversupply fields are useful diagnostics but are not authoritative dispatch-down labels.

The dispatch-down parser reserves: 

- `constraint_mwh`
- `curtailment_mwh`
- `dd_constraint_tso_testing_mwh`
- `dispatch_down_total_mwh`
- wind/solar splits and reason-code fields when present

Keep MWh as the principal modelling target because the publication is an energy quantity over each half hour.

## Leakage warning

Same-period demand, renewable output, availability, SNSP and interconnector flow are valid for nowcasting/diagnostics. They are **not automatically valid day-ahead features**. A genuine forecast must use lagged observations and/or forecasts that were actually known before the prediction timestamp.

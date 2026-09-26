# EirGrid workbooks inspected on 25 Sep 2026

## `System-Data-Qtr-Hourly-2026-V8.xlsx`

This is the useful high-frequency system-context source. The workbook's `System Data` sheet runs from **2026-01-01 00:00 through 2026-08-31 23:45**, with 15-minute average SCADA values.

For January 2026 there are exactly **2,976 quarter-hours**, so every one of the **1,488 half-hours** used by the organiser sample can be formed from two source observations.

Useful fields retained by the importer include:

- IE/NI/all-island demand and generation
- IE/NI/all-island wind availability and actual wind generation
- IE/NI/all-island solar availability and actual solar generation
- IE/NI/all-island batteries; IE/all-island hydro
- EWIC, Greenlink and Moyle interconnector flows
- inter-jurisdictional flow
- all-island oversupply estimate
- SNSP
- wind/solar penetration

Percent/fraction fields in the source workbook are multiplied by 100 and stored with `_pct` suffixes.

### Important January data observations

- EirGrid IE demand vs organiser load: ~0.995 correlation on overlapping observations.
- EirGrid IE wind generation vs organiser onshore wind: ~0.998 correlation.
- The organiser sample reports Irish solar as zero for the month, while EirGrid reports real January solar output (mean ~37.7 MW; maximum ~368.8 MW). Prefer the EirGrid solar field for system modelling.
- `IE Wind Availability - IE Wind Generation` and the equivalent solar difference are retained only as **availability-gap diagnostics**. They are not labelled as dispatch-down because generator market position and other effects can also create a gap.

## `System-and-Renewable-Data-Summary-Report-V29.xlsx`

Useful as a high-level validation/reference workbook, but **not** the half-hourly target dataset.

The KPI tab reports, among other values:

- Ireland wind dispatch-down: **12.81%**, 2026 YTD through August.
- Ireland solar dispatch-down: **11.89%**, 2026 YTD through August.
- Ireland all-renewables dispatch-down: **11.95%**, 2026 YTD through July (the workbook itself uses a different cutoff for this line).

These aggregate percentages should not be expanded into half-hour labels.

## Supervised labels now included

The official **DD Half-Hourly Data** workbooks for 2021–2026 are now integrated. The real training target uses their half-hourly dispatch-down, constraint and curtailment MWh fields. See the [label profile](DD_LABEL_PROFILE.md). `eirgrid_ie_vre_availability_gap_proxy_mw` remains a weak diagnostic/UI proxy only.

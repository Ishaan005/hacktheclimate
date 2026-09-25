# Dispatch-down label profile

Source: official EirGrid/SONI annual `DD-HH` half-hourly workbooks supplied for 2021–2026.

## Exact target semantics

The workbooks explicitly define:

- `DD_MWH = CONSTRAINTS_MWH + CURTAILMENTS_MWH`
- Constraints = transmission constraints + TSO testing
- Curtailments = high-frequency/minimum-generation + RoCoF/inertia + SNSP
- Timestamps are local calendar timestamps; UTC is obtained by subtracting `GMT_OFFSET` hours.

The importer uses the workbook's explicit total columns and reason columns. It does **not** infer dispatch-down from availability minus output.

## Coverage

| Year | IE half-hours | Coverage | Dispatch-down MWh | Constraint MWh | Curtailment MWh |
|---|---:|---|---:|---:|---:|
| 2021 | 17,520 | full year | 752,376 | 460,966 | 291,412 |
| 2022 | 17,520 | full year | 988,478 | 575,653 | 412,827 |
| 2023 | 17,520 | full year | 1,163,282 | 559,141 | 604,143 |
| 2024 | 17,568 | leap year | 1,305,641 | 646,198 | 659,445 |
| 2025 | 17,520 | full year | 1,635,754 | 932,827 | 702,929 |
| 2026 | 11,662 | Jan–Aug workbook | 1,271,173 | 710,386 | 560,791 |

These are absolute energy totals. Do **not** interpret the year-to-year increase as a dispatch-down rate trend without also normalising for installed renewable capacity / available energy.

## January 2026 — organiser sample overlap

All **1,488 / 1,488** organiser half-hours match a real EirGrid IE dispatch-down label.

- Total dispatch-down: **61,182.2 MWh**
- Constraints: **47,288.4 MWh** (77.3% of January DD)
- Curtailments: **13,893.9 MWh** (22.7%)
- Wind DD: **61,089.0 MWh**
- Solar DD: **93.2 MWh**
- Any positive DD: **675 / 1,488 intervals (45.4%)**
- DD > 5 MWh: **571 / 1,488 (38.4%)**
- DD > 10 MWh: **538 / 1,488 (36.2%)**
- Maximum one half-hour: **497.2 MWh**

January reason totals:

- Transmission constraint: **47,288.4 MWh**
- SNSP curtailment: **5,932.3 MWh**
- High-frequency / minimum-generation curtailment: **7,961.8 MWh**
- RoCoF / inertia: **0 MWh** in this January slice

## Quality checks

Across the six official workbooks the formula residuals are only rounding-scale (maximum observed around 0.04 MWh), which is consistent with the workbook totals being rounded independently.

The combined file is `data/processed/dispatch_down_labels_ie_2021_2026.csv`.
The January supervised table is `data/processed/training_table_labeled_jan2026.csv`.

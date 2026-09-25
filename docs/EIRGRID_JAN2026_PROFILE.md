# January 2026 EirGrid context profile

Generated from `System-Data-Qtr-Hourly-2026-V8.xlsx` and aligned to the organiser's 30-minute January sample.

## Coverage

- 2,976 EirGrid quarter-hour intervals in January 2026.
- Aggregates exactly to 1,488 half-hours.
- 1,488 / 1,488 organiser timestamps matched.
- Every retained EirGrid context field has complete January coverage.

## Useful checks against organiser samples

- EirGrid IE demand vs organiser load: correlation ≈ **0.995** on overlapping rows.
- EirGrid IE wind generation vs organiser onshore wind: correlation ≈ **0.998**.
- EirGrid IE solar generation: mean ≈ **37.7 MW**, max ≈ **368.8 MW**. The organiser generation sample reports solar as zero, so use EirGrid solar for system modelling.

## January operating ranges

- IE demand: mean ≈ **4,559.5 MW**, min ≈ **3,308.7 MW**, max ≈ **5,897.1 MW**.
- IE wind generation: mean ≈ **1,504.9 MW**, min ≈ **97.7 MW**, max ≈ **3,685.2 MW**.
- IE solar generation: mean ≈ **37.7 MW**, max ≈ **368.8 MW**.
- SNSP: mean ≈ **49.9%**, max ≈ **74.85%**; 71 half-hours are above 70%.
- EWIC: mean ≈ **241.9 MW**, observed range ≈ **-201.2 to 530.0 MW** under the workbook's source sign convention.
- Greenlink: mean ≈ **310.7 MW**, observed range ≈ **-215.8 to 513.4 MW** under the workbook's source sign convention.
- Moyle: mean ≈ **244.6 MW**, observed range ≈ **-204.4 to 442.1 MW** under the workbook's source sign convention.

## Do not turn availability gap into the target

The raw difference between IE wind/solar availability and actual output is positive almost continuously (1,486 of 1,488 half-hours above 1 MW; mean ≈ 113 MW). That makes it a poor binary dispatch-down label: the gap can reflect generator market position and other operational/measurement effects, not only TSO dispatch-down.

It is correlated with SNSP (≈ +0.65) and negatively correlated with SEM price (≈ -0.36), so it can remain a useful **diagnostic feature**, but the authoritative target must come from EirGrid's separate DD Half-Hourly dataset.

EirGrid's `AI Oversupply` estimate is much rarer in this month (only 3 half-hours above 0.01 MW, max ≈ 42.4 MW). Treat it as another system-pressure indicator, not a replacement for the DD target.

# Network forecast adapter and 48 half-hour scenario screen

`GET /v1/network/forecast` combines **supplied** national constraint predictions,
demand and regional generation forecasts with a static TYTFS planning case. It
does not generate weather, demand or national constraint forecasts itself. With
the current data, it is an architecture and scenario proof, not a validated
operational forecast of line loading or dispatch-down at a site.

## Inputs and run path

1. Re-import the [summer 2024 V33 case](TYTFS_BASE_CASE.md). The updated import
   writes `dc_lines.csv` and records the Scotland converter bus as an explicit
   external boundary. Two RAW DC lines each schedule 40 MW into the modeled
   Irish AC grid. These are study-case settings, not observed transfers.
2. Build `generator_crosswalk.csv` with the [reviewed ECP workflow](NETWORK_GENERATOR_CROSSWALK.md).
   The committed review covers only six Ballylickey station proxies. A regional
   forecast with no reviewed group is rejected.
3. Supply `data/processed/network_forecast_inputs.json` as 48 contiguous UTC
   half-hour rows. Every row needs the same `issue_time` and `forecast_source`,
   plus `valid_time`, `demand_mw`, `constraint_probability`,
   `expected_constraint_mwh`, `forecast_confidence`, and optional
   `regional_generation_mw`, `dc_transfers_mw`, and `drivers`. For example, a
   single row's shape is:

```json
{
  "issue_time": "2026-09-28T16:00:00Z",
  "forecast_source": "example-upstream-model-run",
  "valid_time": "2026-09-28T16:30:00Z",
  "demand_mw": 3402.3,
  "constraint_probability": 0.5,
  "expected_constraint_mwh": 20.0,
  "forecast_confidence": 0.5,
  "regional_generation_mw": {"F:Ballylickey": {"wind": 20.0}},
  "dc_transfers_mw": {"1": 40.0, "2": 40.0},
  "drivers": ["illustrative input only"]
}
```

The numbers above are **illustrative**, not a published forecast. `valid_time`
must start within the next hour for the API and cover 48 consecutive half-hours;
the common `issue_time` must be no later than the request and at most 24 hours
old. A missing input file yields HTTP 503; invalid or stale inputs yield 422.

Set `NETWORK_CASE_DIR`, `NETWORK_GENERATOR_CROSSWALK`, and
`NETWORK_FORECAST_INPUT` if the files are elsewhere. `NETWORK_PLANNED_OUTAGE_ID`
selects the reviewed branch; the default is Cashla–Flagford `1642:2522:1`.
Keep the source and derived workbooks/CSVs/JSON under ignored local storage.

## Calculation and output

The adapter scales the TYTFS in-service load shape to each national demand
value. It allocates each regional wind or solar MW forecast only across
reviewed, connected station proxies in that exact region and technology,
weighted by MEC and capped by their combined MEC. It then dispatches the
remaining in-service generators within Pmin/Pmax. Scheduled or overridden
external DC import reduces the required modeled-grid thermal generation.
The solver applies AC injection overrides **before** DC transfers so an
all-bus override cannot erase an interconnector assumption.

Each half-hour solves the intact and planned-outage topologies. At the
most-stressed planned-outage half-hour, a bounded screen tests up to ten
highest-loaded rated assets as additional contingencies. The most stressed
operable screened contingency is replayed across the horizon. The response
keeps the three scenario summaries, the screened islanding candidates, and
the upstream forecast source and issue time. Islanded branch flows and deltas
are suppressed as non-operable; `security_event` is a screening flag, not an
EirGrid N-1 verdict. A contingency outside the bounded candidate set may be
more severe.

The rating comparison is `abs(DC active MW) / RAW rate A MVA`, a unity-power
factor screening proxy. The model omits AC voltage, reactive power, losses,
dynamic security, actual switch state and measured line flows. The scheduled
Cashla–Flagford outage is a reviewed asset match, not evidence that the line
is actually open.

`scripts/forward_constraint.py` can optionally join historical network
features to a training frame only when both `issue_time` and `valid_time`
are present. It selects the latest forecast for the target half-hour issued
by the decision time. This prevents later network revisions from leaking into
historical backtests, but it does not create the missing historical forecasts.

## Verified local check

On the downloaded TYTFS case, import and the reviewed
[Cashla scenario](NETWORK_SCENARIO_DEMO.md) solve with the two 40 MW DC lines.
An explicitly synthetic 48-row input using the Ballylickey proxy returned
48 records through the local HTTP endpoint. The full test suite covers the
parser, DC and islanding behavior, allocation, forecast contract and the
point-in-time feature join. The synthetic input and response remain untracked.

# Safety and flexible-action screen

`GET /v1/operator/view` extends the [48 half-hour network forecast](NETWORK_FORECAST_ARCHITECTURE.md)
with a conservative safety result and a small action screen. It uses the same
local case, reviewed generator crosswalk and point-in-time upstream forecast.
An absent action catalog appears in `health.missing_inputs`.

## Safety semantics

Each scenario reports `thermal`, `islanding`, `snsp`, `voltage`, `inertia`, and
`rocof` as `PASS`, `FAIL`, or `UNKNOWN`. Any failed check makes the overall result
`FAIL`; otherwise an unknown check makes it `UNKNOWN`. An action enters the
screening-pass ranking only when **every required check passes**. The current
endpoint leaves voltage, inertia and RoCoF unknown because a DC study case
cannot evaluate them. It therefore issues **no safe recommendation**.

Thermal checks compare modeled active MW with TYTFS rate A MVA. A proxy over
100% fails the modeled check; missing ratings make it unknown. This is not an
AC thermal-security verdict. Islanding uses the AC topology screen. SNSP is
checked only when a point-in-time `snsp_pct` is supplied for the unchanged
forecast state; 75% is the scenario rule from [issue #5](https://github.com/Ishaan005/hacktheclimate/issues/5),
not a claim about the current operating limit. The action screen leaves SNSP
unknown because extra renewable generation and load change its inputs and no
validated action-level SNSP calculation is available.

## Controlled action input

Set `NETWORK_ACTION_CANDIDATES` to a local JSON file with up to three reviewed
candidate locations. Keep it in ignored `data/processed/` along with its source
evidence. The file shape is:

```json
{
  "actions": [{
    "action_id": "example-flex-load",
    "load_bus_id": 123,
    "renewable_bus_id": 456,
    "allocation_region": "reviewed-region",
    "generation_type": "wind",
    "power_mw": 10,
    "available_from": "2026-09-29T00:00:00Z",
    "available_until": "2026-09-29T01:00:00Z",
    "review_status": "accepted_proxy",
    "evidence_reference": "reviewed-source-row"
  }]
}
```

The renewable bus must match an accepted region and technology in the generator
crosswalk; both buses must be active. The load-bus review and availability
reference must be supplied separately. The example IDs above are placeholders,
not mapped TYTFS assets.

Each upstream forecast row may supply
`"recoverable_renewable_mw": {"reviewed-region": {"wind": 10}}`. This is
additional renewable MW that could be generated **above the forecast baseline**
if local demand is added. It must come from a documented, point-in-time source;
the current datasets do not establish it. Without it, the candidate has zero
modeled opportunity. The screen also caps action MW by the reviewed source
generator MEC and the supplied national expected constraint MWh.

For an eligible half-hour, the screen adds renewable injection at the reviewed
generator bus and the same demand at the flexible-load bus, then re-solves the
planned-outage network. The response compares the base and action stress
features and reports a `modeled_capture_upper_bound_mwh` of applied MW times
0.5 hours. This is an upper bound, **not expected avoided constraint MWh**.
`expected_avoided_constraint_mwh` and `recommendation` remain null until a
validated locational impact model and all required safety evidence exist.

## Data and API behavior

With required forecast files missing, the route returns 503. Invalid or stale
forecast rows, action catalogs, or asset references return 422. A valid
forecast with absent action/effect evidence still returns 48 forecast rows and
health gaps, with no recommendation. The response includes source forecast
issue time, source name and the planning-case vintage. This permits an operator
view to show what was evaluated without presenting a synthetic action as safe.

The existing [forecast-safe baseline work](FORWARD_CONSTRAINT_FORECAST.md) and
[issues #6–#8](https://github.com/Ishaan005/hacktheclimate/issues/6) still need
archived point-in-time weather and publication-latency evidence before a real
1–24 hour forecast can feed this route. No synthetic forecast or action file is
committed.

# Operator case evaluation

`POST /v1/operator/evaluate` accepts a `decision_case`, exactly 48 half-hour
`forecast_rows`, `action_candidates`, and separately sourced energy `evidence`.
The same request can be run locally:

```bash
.venv/bin/python -m scripts.run_operator_evaluation --example \
  --output data/raw/network_case/operator_example_output.json
.venv/bin/python -m scripts.run_operator_evaluation \
  --request examples/operator_evaluation/operator_example_output.request.json \
  --output data/raw/network_case/operator_example_rerun.json
```

With the API running, the same request can be posted:

```bash
curl -sS http://127.0.0.1:8000/v1/operator/evaluate \
  -H 'Content-Type: application/json' \
  --data-binary @examples/operator_evaluation/operator_example_output.request.json
```

The example uses the **real TYTFS 2024 planning topology** and reviewed
Ballylickey generator-to-station proxy. Its demand, regional generation,
constraint, curtailment, recoverable renewable MW and flexible load actions are
invented scenario assumptions. The example's `scenario_assumption` action
status is never a safety pass. Neither file represents an operational forecast,
measured dispatch-down, an approved action, or avoided energy. Generated files
have checked-in copies at
[`examples/operator_evaluation/operator_example_output.request.json`](../examples/operator_evaluation/operator_example_output.request.json)
and [`examples/operator_evaluation/operator_example_output.json`](../examples/operator_evaluation/operator_example_output.json).
The commands above write fresh local results under ignored `data/raw/`.

## Input contract

- `decision_case` follows `DecisionCase`: decision time, future 24-hour window,
  scenario IDs, and any existing instructions. Its start must match the first
  forecast half-hour.
- `forecast_rows` follow the [network forecast contract](NETWORK_FORECAST_ARCHITECTURE.md).
  All 48 rows share one issue time and source. The request supplies
  `forecast_available_at`, `forecast_version` and
  `forecast_evidence_reference`; availability must be no later than the
  decision time. Each row supplies demand, national constraint probability
  and expected MWh, and any reviewed regional generation and DC transfers.
- `evidence` follows `EvidenceValue`. Supply `constraint_mwh` and
  `curtailment_mwh` for each half-hour, including source version, issued time,
  availability time, freshness limit and valid time. Missing or stale values
  stay missing. Supplied constraint values must agree with the national MWh
  values in `forecast_rows` before they can be compared. Existing instructions
  are applied only when they are not already reflected in source forecasts.
- `action_candidates` follow the [flexible action contract](NETWORK_SAFETY_ACTIONS.md).
  The current solver supports paired local renewable generation and flexible
  demand or charging. An unreviewed planning action may use
  `scenario_assumption`; it can expose flow changes but cannot pass safety.
  Other action families in `config/operator_actions.txt` are descriptive
  placeholders and have no executable transformation yet.

The HTTP route uses the configured local TYTFS case, generator crosswalk and
planned outage. It returns 422 for malformed or inconsistent inputs and 503
when local case files are missing. The CLI accepts the same request JSON.

## Output and limits

`current_plan` contains all 48 interval constraint, curtailment and total
dispatch-down MWh values, sums, source versions, missing reasons and the
versioned demo safety-policy result. `forecast` contains intact, planned-outage
and selected N-1 network summaries. Each evaluated action has paired base and
action states, the ten largest signed flow changes per scenario, safety checks
and a **modeled capture upper bound**. The bound is at most the action's MW ×
half-hour duration, regional recoverable-MW assumption, generator MEC
headroom and supplied national expected constraint MWh.

`ranked_modeled_capture_bounds` is an exploratory sort of all simulated
actions with their safety labels. It is not an avoided-energy ranking.
`ranked_expected_avoided_dispatch_down` and `recommendation` remain empty/null:
DC flow changes alone do not establish how much constraint or curtailment an
operator would avoid. The current case also lacks a complete approved safety
calculation for voltage, reserves, system strength, frequency, inertia, RoCoF,
asset capability and action timing. `decision_contract_status` also reports
the current scenario/action/outcome contract review gate. A locational impact model needs reviewed
case-level dispatch-down outcomes and independent validation before these
fields can be populated.

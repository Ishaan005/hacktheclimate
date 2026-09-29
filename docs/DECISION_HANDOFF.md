# Case-flow handoff before scenario and action approval

The independent backend pieces from issue #32 now run through `POST /v1/decision/preview`. The request supplies a typed case and optional search conditions. The server reads only its checked national GFS constraint snapshot; clients cannot submit a forecast or safety pass. The response includes 48-interval evidence coverage, a current-plan baseline, policy results, comparable cases when explicitly requested, and blocking reasons. It always returns `recommendation: null` because action selection and approved safety inputs are not connected.

Run `python -m scripts.smoke_decision_preview` from the repository root to exercise the route in process. A missing or expired forecast is a normal, explicit `unavailable` result. To create a current snapshot, first follow [the checked GFS inference runbook](GFS_INFERENCE.md). That snapshot contains national **constraint** estimates only; curtailment and total dispatch-down remain unavailable.
For a case with a named location or asset, the national snapshot is marked `inapplicable` and its values do not enter the baseline.

The preview defaults to an empty case library. Set `include_modelled_demo_cases: true` in a request only when intentionally showing the three synthetic examples. Those results retain their `modelled` label. The endpoint makes no changes to case records.

## Inputs to lock with Jack

The [pending contract manifest](../config/decision_contract_status.json) records that these decisions have not been approved. Do not change its status to `approved` without a source reference and all of the following:

1. Stable scenario IDs, ordinary-language definitions, identification facts, and the rule for simultaneous or unknown causes (roadmap 01).
2. Stable action IDs, runnable versus preview-only status, asset capability and timing inputs, and operator measures (roadmap 02).
3. For every scenario, required facts with units, allowed source types, freshness limits, and `once` or `half_hour` cadence; eligible actions and clarification triggers (roadmap 03).
4. Agreed current-plan, post-action, avoided-energy, cost, unavailable, and zero-baseline definitions (roadmap 07).

After approval, populate the manifest, add a test for each selected scenario, then map the approved facts into `DecisionCase` evidence. The manifest validator checks their units, source types, freshness, and time coverage. Attach reviewed current measurements and planning checks to the same decision time. The policy still needs reviewed formulas and limits for the unsupported checks; a manifest approval by itself cannot make an action safe.

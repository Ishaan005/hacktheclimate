# Case-flow handoff before scenario and action approval

The independent backend pieces from issue #32 now run through `POST /v1/decision/preview`. The request supplies a typed case and optional search conditions. The server reads only its checked national GFS constraint snapshot; clients cannot submit a forecast or safety pass. The response includes 48-interval evidence coverage, a current-plan baseline, policy results, comparable cases when explicitly requested, and blocking reasons. It always returns `recommendation: null` because action selection and approved safety inputs are not connected.

Run `python -m scripts.smoke_decision_preview` from the repository root to exercise the route in process. A missing or expired forecast is a normal, explicit `unavailable` result. To create a current snapshot, first follow [the checked GFS inference runbook](GFS_INFERENCE.md). That snapshot contains national **constraint** estimates only. For all issue #47 scenarios it is marked `inapplicable` and cannot populate the scenario baseline; curtailment and total dispatch-down remain unavailable too.

The preview defaults to an empty case library. Set `include_modelled_demo_cases: true` only when intentionally showing the three synthetic examples. They retain their `modelled` label and legacy scenario IDs; issue #47 does not justify mapping them to T1–T4, H1–H4, or SNSP. A new catalogue case will therefore find no comparable demo records. The endpoint makes no changes to case records.

## Locked scenario catalogue

[Issue #47](https://github.com/Ishaan005/hacktheclimate/issues/47) locks the product labels T1–T4, H1–H4, and one SNSP case. `GET /v1/decision/scenarios` returns their selection boundaries, three transmission reaches, tracked variants, and named intake fields from [the versioned catalogue](../config/decision_scenarios_v1.json). A case can carry several labels when requirements overlap. If the limiting cause is missing, submit `cause_unknown: true` with `scenario_ids: []`; this is an intake state and blocks a recommendation. Unknown or legacy labels are reported as contract gaps.

The preview returns `scenario_intake` for each selected label, listing recorded and missing identification fields. `classification_verified` stays false because field presence is not proof that a limiting rule binds. H1's frequency field counts as recorded only when backed by measurement evidence.

The catalogue names what to collect. It does not supply a policy limit, a verified source, a freshness rule, or evidence that a particular case meets a label. The T/H labels are product labels, not separate published dispatch-down reason codes. A national constraint forecast alone cannot identify a T case or an H/SNSP limiting requirement.

## Inputs to lock with Jack

The [pending contract manifest](../config/decision_contract_status.json) now records #47 as the locked scenario source. Do not change the overall status to `approved` without a source reference and all of the following:

1. Stable action IDs, runnable versus preview-only status, asset capability and timing inputs, and operator measures (roadmap 02).
2. For every locked scenario, required facts with units, allowed source types, freshness limits, and `once` or `half_hour` cadence; eligible actions and clarification triggers (roadmap 03).
3. Agreed current-plan, post-action, avoided-energy, cost, unavailable, and zero-baseline definitions (roadmap 07).

After approval, populate the manifest, add a test for each selected scenario, then map the approved facts into `DecisionCase` evidence. The manifest validator checks their units, source types, freshness, and time coverage. Attach reviewed current measurements and planning checks to the same decision time. The policy still needs reviewed formulas and limits for the unsupported checks; a manifest approval by itself cannot make an action safe.

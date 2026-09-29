# Operator workspace backend handoff (issue #61)

`GET /v1/workspace/brief` returns the locked T1–T4, H1–H4 and SNSP catalogue, supported view names and action check IDs. Use its descriptions for situation suggestions. It does not identify a cause from free text; send reviewed scenario IDs to the assessment route. Multiple IDs may bind at once.

`POST /v1/workspace/assess` accepts a `DecisionCase`, provenance-bearing `EvidenceValue` rows, a proposed plan and an operator alternative. Its request and response types are in [workspace-brief.ts](ui-handoff/workspace-brief.ts). The decision window is exactly 24 hours and starts at a future UTC half-hour relative to `as_of`. Step dependencies must refer to earlier steps. The response returns a stable `revision` hash of all request inputs. The UI should mark the displayed assessment stale as soon as a fact or step changes, then replace it after a new request completes. The audit ID is a request fingerprint; `audit_persisted: false` means no durable audit record has been written.

The response includes:

- Top bar: `view`, `location`, `decision_time`, `window`, `source_status` and `data_status`.
- Situation review: `bindings`, `facts`, and `active_instructions`. Each fact carries source, time, type and current/stale/missing/conflicting state. Conflicting facts have a null display value and retain their individual observations.
- Safety and plan panels: each of the four `comparisons` has family and action check rows, overall safety, a plan label, steps, dependencies, permission status, timing and MW fields. The site view retains all selected all-island checks.
- Outcome panel: current plan, no new instruction, proposal and alternative share one window and the same existing instructions. Constraint and curtailment MWh remain separate. Unsupported benefits have null values and a reason.
- Evidence drawer: catalogue version, missing checks, assessment time, source status and audit ID.

The current frontend uses [the adapter](../frontend/src/decision/backend.ts) to
turn the endpoint's snake_case response into the decision workspace view model.
It sends only reviewed condition details and operator-entered facts. The UI
does not send a safety result or benefit estimate. A proposed plan remains
empty unless the backend can substantiate one; the UI allows an operator
alternative to be entered and rechecked separately.

Example request (with the API running):

```bash
curl -sS http://127.0.0.1:8000/v1/workspace/assess \
  -H 'Content-Type: application/json' \
  -d '{"decision_case":{"case_id":"review-1","scenario_ids":["T2","SNSP"],"location":"site-a","as_of":"2026-09-29T10:00:00Z","starts_at":"2026-09-29T10:30:00Z","ends_at":"2026-09-30T10:30:00Z"},"view":"site","site_id":"site-a","proposed_plan":{"steps":[{"step_id":"charge-1","action_id":"STORAGE_CHARGE","asset_or_party":"battery-a","permission":"pending","limiting_location_delta_mw":-5}]},"operator_alternative":{"steps":[]}}'
```

The current assessment has **no live operational feed or approved safety study**. Supplied evidence is displayed with provenance and freshness, but it cannot certify a safety pass. All required family and action checks therefore remain `UNKNOWN` unless a permission is explicitly denied, which yields `FAIL`. No plan can be `Actionable` or `Conditional` yet. The response uses `no_live_connection`; the existing `/v1/workspace/evaluate` planning result is separately badged `planning_case`, and its fallback is `no_live_connection`. The site risk, avoided dispatch-down, cost and carbon fields remain `Not established` until independently validated case-level methods and sources exist. A current-plan/no-new-instruction distinction will need a connected operational forecast that applies active instructions over time.

Before an operator-facing release, connect and validate the effective EirGrid/SONI limits, live feeds, full contingency and dynamic studies, action authority and timing, and outcome models listed in [issue #61](https://github.com/Ishaan005/hacktheclimate/issues/61). Keep the assessment endpoint read-only: it does not send grid instructions.

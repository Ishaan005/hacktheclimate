# Operator workspace backend handoff (issue #61)

`GET /v1/workspace/brief` returns the locked T1–T4, H1–H4 and SNSP catalogue, supported view names and action check IDs. Use its descriptions for situation suggestions. It does not identify a cause from free text; send reviewed scenario IDs to the assessment route. Multiple IDs may bind at once.

`POST /v1/workspace/assess` accepts a `DecisionCase`, provenance-bearing `EvidenceValue` rows, a proposed plan and an operator alternative. Its request and response types are in [workspace-brief.ts](ui-handoff/workspace-brief.ts). The decision window is exactly 24 hours and starts at a future UTC half-hour relative to `as_of`. Step dependencies must refer to earlier steps. The response returns a stable `revision` hash of all request inputs. The UI should mark the displayed assessment stale as soon as a fact or step changes, then replace it after a new request completes. The audit ID is a request fingerprint; `audit_persisted: false` means no durable audit record has been written.

The response includes:

- Top bar: `view`, `location`, `decision_time`, `window`, `source_status` and `data_status`.
- Situation review: `bindings`, `facts`, and `active_instructions`. Each fact carries source, time, type and current/stale/missing/conflicting state. Conflicting facts have a null display value and retain their individual observations.
- Safety and plan panels: each of the four `comparisons` has family and action check rows, overall safety, a plan label, steps, dependencies, permission status, timing and MW fields. The site view retains all selected all-island checks.
- Outcome panel: current plan, no new instruction, proposal and alternative share one window and the same existing instructions. Constraint and curtailment MWh remain separate. Unsupported benefits have null values and a reason.
- Evidence drawer: catalogue version, missing checks, assessment time, source status and audit ID.

The operator screen omits facts, check rows, comparison measures, plan fields,
and benefit cards when they have no usable value. It also hides assessment
metadata until an assessment exists. This is a display choice: the API keeps
null values, missing evidence, and `UNKNOWN` safety gates so absent data cannot
be mistaken for zero or an approved action. Missing check details remain in
the evidence drawer.

For a historical or synthetic planning demo, the top bar names the demo source
and assessment time without repeating a page-level `Missing` badge. The safety
panel shows one concise Unknown explanation; its full reason and exact missing
checks are expandable. Modeled outcome numbers use one demo caveat rather than
repeating it on every card. The experimental national forecast text moves to
the evidence drawer. These presentation changes do not change safety or
benefit validation.

The current frontend uses [the adapter](../frontend/src/decision/backend.ts) to
turn the endpoint's snake_case response into the decision workspace view model.
It sends only reviewed condition details and operator-entered facts. The UI
does not send a safety result or benefit estimate. A proposed plan remains
empty unless the backend can substantiate one; the UI allows an operator
alternative to be entered and rechecked separately.

The assessment fills case context that is explicit in the request: a reviewed
condition's asset/reach/outage/time setting, `planned outage` or `forced outage`
and `next N hours` when those exact phrases appear in the operator description,
and `forecast` for the future assessment window. These rows identify their
source as case context or operator description. They are not operational feed
measurements. Missing rows carry a specific reason, including the absence of a
connected instruction log, measurement, or effective policy.

For the packaged Ballylickey example only, the synthetic four-bus planning
case also supplies a named demo route and outage, affected demo wind group,
local reach, computed baseline DC flow, and its rate A MVA proxy. These rows
are marked `modeled` and sourced to the synthetic case; they remain in
`bindings.missing_fields` until operational evidence is supplied. The MVA
rating is shown in a separate planning row and is never used as an MW operating
limit. The planning line check shows its modeled loading against 100% of rate A
and uses the correct baseline or proposed margin. The response still leaves
the real outage return time, current instructions and operational flow limit
missing, and safety remains unapproved. Curtailment MWh remains unknown because
the demo does not model it; the operator screen omits that measure until data
exists.

When a checked GFS snapshot is available at the decision time and covers the
first assessment half-hour, `national_constraint_context` reports its
experimental national constraint estimate and model interval. The frontend
shows it only as national context while omitting the unavailable site risk. It does not
fill local route flow, curtailment, safety, or an action benefit. Historical
January–August measurements and the 2024 TYTFS planning topology likewise do
not fill a September 2026 future operational case.

Example request (with the API running):

```bash
curl -sS http://127.0.0.1:8000/v1/workspace/assess \
  -H 'Content-Type: application/json' \
  -d '{"decision_case":{"case_id":"review-1","scenario_ids":["T2","SNSP"],"location":"site-a","as_of":"2026-09-29T10:00:00Z","starts_at":"2026-09-29T10:30:00Z","ends_at":"2026-09-30T10:30:00Z"},"view":"site","site_id":"site-a","proposed_plan":{"steps":[{"step_id":"charge-1","action_id":"STORAGE_CHARGE","asset_or_party":"battery-a","permission":"pending","limiting_location_delta_mw":-5}]},"operator_alternative":{"steps":[]}}'
```

The current assessment has **no live operational feed or approved safety study**. Supplied evidence is displayed with provenance and freshness, but it cannot certify a safety pass. All required operational family and action checks therefore remain `UNKNOWN` unless a permission is explicitly denied, which yields `FAIL`. The packaged Ballylickey example can add explicitly synthetic planning checks and scenario-assumption energy values; they do not approve a real action. No plan can be `Actionable` or `Conditional` yet. The response uses `no_live_connection` or `planning_case` when the planning evaluator runs. The site risk, validated avoided dispatch-down, cost and carbon fields remain `Not established` until independently validated case-level methods and sources exist. A current-plan/no-new-instruction distinction will need a connected operational forecast that applies active instructions over time.

Before an operator-facing release, connect and validate the effective EirGrid/SONI limits, live feeds, full contingency and dynamic studies, action authority and timing, and outcome models listed in [issue #61](https://github.com/Ishaan005/hacktheclimate/issues/61). Keep the assessment endpoint read-only: it does not send grid instructions.

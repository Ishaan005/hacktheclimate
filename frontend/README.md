# Operator screen

Use a supported Node 22 release, then run the FastAPI server on
`127.0.0.1:8000` and start the UI:

```bash
npm ci
npm run dev
```

## Decision workspace (main screen)

The main screen follows the [UI brief](../docs/UI_BRIEF_2026-09-29.md). It has
a top bar (national or site view, source badge), a free-text situation box
with an Assess button, the situation table, safety checks (left),
the proposed plan (right), a four-column comparison and an evidence drawer.
The code is in `src/decision/` (types, display rules, locked scope, fixture,
API) and `src/components/decision/`.

In default API mode, the screen sends the operator's text as typed, locked
scenario hints read from it (`hintsFor` in `src/decision/scope.ts`), operator
fact edits and alternative steps to `POST /v1/workspace/assess`. Text with no
scenario in scope shows Cause unknown and the facts needed. The adapter in
`src/decision/backend.ts` maps the response into the screen's view model. The
backend currently has no live operational feed or approved safety study, so
the screen shows **No live connection**, unknown checks and unestablished
benefits. An operator can create an alternative even when the backend has no
proposal; edits remain out of date until reassessed. `src/decision/rules.ts`
only makes the display more cautious and never creates a safety result. Use
`VITE_API_MODE=fixture npm run dev` for the separate historical demonstration.

## Grid assistant (second tab)

The screen is one input field. The operator describes the situation and the
workspace shows the returned scenario: binding condition, recommended action,
baseline vs post-action outcome and guardrails. The recommended action carries
`steps`: the ordered actions the operator takes, shown in a dropdown list. An
LLM scenario solver will supply that scenario; until it is linked, live mode says the solver is not
connected. Connect it in `solveSituation` in `src/api.ts`, which must return a
`SolverResult` (see `src/types.ts`) or `null` for no match. A result is either a
`scenario` or a `dispatch_down_risk` view for a UTC half-hour; the latter shows
the next-hour card and day chart from `/v1/dispatch-down/forecast` and
`/v1/dispatch-down/forecast/day` (historical January 2026 replay).

For layout work without backend inputs, use the offline fixture explicitly:

```bash
VITE_API_MODE=fixture npm run dev
```

In fixture mode, descriptions are keyword-matched against the invented
scenarios in `src/fixtures/illustrativeScenarios.ts`, labelled as illustrative.
They are layout samples, not model results. Try "line overload in the west",
"low voltage north-west evening" or "SNSP overnight". A description containing
"dispatch-down" returns the replay view, at a time such as "2026-01-20 14:30"
if one is named.

The workspace follows [UX plan](../docs/UX_PLAN_10PM28.md) phase 1. The earlier
forecast, planning and network panels are not on screen; their components and
tests remain for phase 3.

Run `npm test`, `npm run lint`, and `npm run build` before changing the UI.

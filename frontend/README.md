# Operator screen

Use a supported Node 22 release, then run the FastAPI server on
`127.0.0.1:8000` and start the UI:

```bash
npm ci
npm run dev
```

The screen is one input field. The operator describes the situation and the
workspace shows the returned scenario: binding condition, recommended action,
baseline vs post-action outcome and guardrails. The solver may also return
`alternatives`: other evaluated actions, best first, each with its own outcome
and the reasons it ranks lower. They render below the recommendation. An LLM
scenario solver will supply that scenario; until it is linked, live mode says the solver is not
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

# Operator screen

Use a supported Node 22 release, then run the FastAPI server on
`127.0.0.1:8000` and start the UI:

```bash
npm ci
npm run dev
```

The screen is one input field. The operator describes the situation, reviews
the extracted facts, and the workspace shows the returned scenario: binding
condition, recommended action when one is evidence-supported, baseline vs
post-action outcome and guardrails.

Live mode uses the existing UI as the contract:

- `POST /v1/intake` extracts only operator-stated facts (LLM with rule fallback)
  into the current fact-review case.
- `POST /v1/workspace/evaluate` accepts that reviewed case, runs the configured
  decision/network/action backend, and returns the existing `WorkspaceScenario`
  shape.

Missing planning files, unresolved scenario detail, unsupported safety checks,
or unvalidated avoided-energy estimates return a live workspace with no
recommended action and explicit reasons. Direct dispatch-down/chat questions
keep their existing routes.

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

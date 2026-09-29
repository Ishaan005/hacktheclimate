# Interaction decision (Issue 04A)

Decision recorded 29 September 2026 for build issue 04A in [#32](https://github.com/Ishaan005/hacktheclimate/issues/32). The action list follows the four core actions in [#21](https://github.com/Ishaan005/hacktheclimate/issues/21): storage charging, flexible demand, generator redispatch, and planned-outage review. Voltage and stability support stay in the expanded MVP.

## Decision

Use a **combined** interface:

1. The operator describes the situation in one plain-English text box. They may add an action of their own or a second situation to compare.
2. The tool extracts a structured case and shows it as a **fact review table**. Each row shows value, unit, source, time, and status.
3. Missing required facts appear as **form questions** ranked by what blocks the decision. The operator answers or corrects facts in place.
4. Chat stays available beside the result for "why" questions and evidence lookup. Chat never changes a fact on its own: any change goes back through the fact table.

The case types live in [`frontend/src/case.ts`](../frontend/src/case.ts). They are provisional until the Issue 01–03 scenario and fact lists are approved.

## Options compared

| Criterion | Chat only | Custom form only | Combined |
| --- | --- | --- | --- |
| Input speed | Fast first message | Slow: many fields before anything happens | Fast: one sentence starts the case |
| Clarity | Facts are scattered across messages | Every fact is visible | Every fact is visible in one table |
| Correction | Operator must retype and hope the model updates the right fact | Edit the field | Edit the row; source changes to operator |
| Clarification | Questions arrive one at a time with free-text answers that need parsing again | Operator must find the empty fields themselves | Ranked questions with typed controls (number, choice) and units |
| Comparison entry | An alternative action in free text is easy to misread | Needs a second full form | Optional second text box, same review table and questions |

Chat alone fails on correction and on units. A form alone is slow and gives the operator no help finding what matters. The combined approach keeps the speed of free text and the precision of a form.

The current app already has the parts: `SituationInput` (free text), `ClarificationForm` (typed questions), and the LangGraph assistant (`/v1/chat`). What is missing is the case record and the fact review step between them.

## Sample operator journey

Illustrative only: assets and numbers are made up. Situation: wind in the north-west is forecast to exceed a local export limit tomorrow afternoon while a battery is available.

1. **Describe.** The operator types: *"NW constraint expected 14:00–17:00 tomorrow, Battery A is available, can we absorb some of it?"*
2. **Review extracted facts.** The table shows:

   | Fact | Value | Source | Status |
   | --- | --- | --- | --- |
   | Scenario | Local network constraint | Operator text | Supplied |
   | Event window | 14:00–17:00 | Operator text | Supplied |
   | Affected area | North-west | Operator text | Supplied |
   | Expected dispatch-down | 62 MWh (range 30–95) | National forecast, issued 06:00 | Forecast |
   | Proposed action | Storage charging, Battery A | Operator text | Supplied |
   | Maximum charging MW | 50 MW | Asset register | Verified |
   | State of charge | — | — | Unknown |
   | Activation delay | — | — | Unknown |

3. **Answer blocking questions.** Two questions appear, highest priority first:
   - "What is Battery A's state of charge at 14:00?" (number, %)
   - "How long does Battery A need from instruction to charging?" (number, minutes)
4. **Correct a fact.** The operator changes the event window end to 18:00. The row status becomes *Corrected* and the case keeps the earlier value in its history.
5. **Add a comparison.** In the optional box the operator types: *"Compare with reducing Generator B by 40 MW."* The same review table and questions run for the redispatch action, on the same case and baseline.
6. **Stop or continue.** If a required fact is still unknown, the case stops with a list of the missing facts and no recommendation. Otherwise it goes to evaluation and then the comparison and decision screens (Issues 17 and 18).

## What Issue 04 must build

- One text input for the situation, with an optional second input for an operator action or a second situation.
- A fact review table. Each row shows value, unit, source, time, and status (supplied, verified, forecast, corrected, stale, unknown), and has an edit control.
- A question panel that reuses `ClarificationForm`, fed by the case's missing required facts in priority order.
- A clear stop state that names each missing fact. The tool makes no recommendation while one is missing.
- The case saved in one place so answers and corrections survive a round trip to the solver and a page reload.

## Open points

- Scenario families in `case.ts` are a first draft of Issue 01. Jack approves the final list.
- Required and optional facts per action come from the #21 metric tables and acceptance criteria. Issue 03 review may move facts between required and optional.
- The frontend `ActionFamily` type now matches the four #21 core actions. Interconnector requests, voltage and stability actions were removed from the recommendation card and illustrative scenarios.
- The frontend calls `POST /v1/intake` to extract the case. No backend route exists yet: until one does, live mode starts an empty case and the operator supplies every fact. Fixture mode fills facts from the illustrative scenarios.

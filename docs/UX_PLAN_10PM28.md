# UX Plan: EirGrid MVP Scenario Decision Tool

## Goal

Build a frontend that helps an operator answer four questions fast:

1. What is the binding condition?
2. What action is recommended?
3. Can it be executed in time?
4. What changes if the action is taken?

The product is advisory. It recommends a complete operator instruction, but it does not send instructions to assets or external systems.

## Product principle

The UI should feel like an operator console, not a generic analytics dashboard.

The default view should be compact, readable, and decision-focused. Supporting evidence should be available on expansion rather than dumped into the main screen.

## Primary workflow

The MVP should be built around one collapsed scenario workspace:

**Scenario → Binding condition → Recommended action → New outcome**

This is the main user journey. The operator should land directly in this view with the recommended action already selected.

## Core screen structure

### 1. Scenario workspace

This is the main screen.

Layout order:

- Scenario summary
- Binding condition
- Recommended action
- New outcome

Below the main strip, provide expandable sections for:

- Assumptions
- Alternative actions
- Engineering evidence
- Metric definitions

### 2. Scenario list

Provide a lightweight list or left-hand rail of scenarios so the operator can switch context quickly.

Each scenario row should show:

- Scenario name or interval
- Binding condition
- Recommended action type
- Security result
- Avoided dispatch-down waste
- Net financial value
- Earliest achievable execution

### 3. Scenario detail area

Use a drawer, side panel, or expandable section for deeper detail instead of forcing navigation to a new page.

This area should hold:

- Full guardrail before/after results
- Cost breakdown
- Carbon assumptions
- Action feasibility details
- Alternative-action ranking reasons

## Information hierarchy

The operator should see the most important information first.

Recommended content order inside the scenario workspace:

1. Binding condition
2. Recommended instruction
3. Post-action security result
4. Avoided dispatch-down waste
5. Net financial value
6. Estimated avoided emissions
7. Earliest achievable execution
8. Expanded assumptions and evidence

Do not put commercial metrics ahead of security.

## Key UI modules

### Scenario header

Show:

- Scenario title or interval
- Advisory status
- Last model run timestamp
- Comparison mode selector

Default comparison should be baseline vs recommended action.

### Binding condition card

This card explains why action is needed.

Show:

- Binding condition type
- Failed or limiting metric
- Location or affected area
- Margin to limit
- Status: within_modelled_limit, breach, or unknown

The binding guardrail should be the most visually prominent guardrail object on screen.

### Recommended action card

This is the most important component in the product.

Every recommendation should show a complete instruction in plain language, not a category label.

Include:

- Asset name and location
- Current state
- Target state
- Issue time
- Start time
- Target-achievement time
- Effective-until time
- Action family
- Earliest achievable execution

The card should read like an actual dispatch instruction.

Example:

> Issued 14:55 — Generator A to 100 MW by 15:10, effective until 16:30.

### Outcome comparison panel

Show baseline and post-action outcomes side by side on desktop, and stacked on smaller screens.

Always include:

- Baseline dispatch-down waste
- Post-action dispatch-down waste
- Avoided dispatch-down waste
- Dispatch-down reduction
- Gross market opportunity
- Net financial value
- Estimated avoided emissions
- Post-action security result

If baseline dispatch-down waste is zero, show dispatch-down reduction as **N/A**, not zero.

### Guardrail strip

Provide a compact before-and-after strip for:

- Voltage
- Thermal capacity
- SNSP
- Inertia
- Frequency

Each item should show:

- Baseline state
- Post-action state
- Margin
- Timestamp where relevant
- Unknown state where applicable

Unknown must never be presented as safe.

### Evidence and assumptions accordion

Keep technical detail out of the default view, but easy to open.

Include:

- Formula explanations
- Carbon-factor source and year
- Cost assumptions
- Asset capability assumptions
- Modelling caveats
- Alternative ranking reasons

## Action-specific detail design

Use one shared action shell and render family-specific fields inside it.

### Generator active-power output

Show:

- Current MW
- Target MW
- Ramp rate
- Minimum stable generation
- Maximum output
- Services retained or lost
- Estimated redispatch cost

### Commitment state change

Show:

- Current commitment state
- Target commitment state
- Hot, warm, or cold status
- Synchronisation or shutdown timings
- Minimum on/off times
- Inertia, reserve, and reactive contribution
- Start, stop, and minimum-run costs

### Storage charging

Show:

- Current state of charge
- Minimum and maximum state of charge
- Charging MW target
- Available charging MWh
- Ramp rate
- Efficiency and loss assumption
- Rebound requirement
- Charging, loss, and degradation costs

### Voltage or reactive-power control

Show:

- Current and target voltage
- Current and target Mvar
- Reactive capability at present MW
- Tap positions
- Response time
- Expected voltage-margin improvement
- Thermal or voltage side effects elsewhere

### Renewable active-power limit

Show:

- Constraint group or affected units
- Total MW reduction
- Start and end time
- Dispatch reason
- Expected dispatch-down waste
- Remaining security margin

### Interconnector flow change

Treat this as conditional unless confirmed.

Show:

- Interconnector and direction
- Requested MW
- Existing scheduled flow
- Transfer capacity
- Ramp limits
- Earliest feasible interval
- Counterparty coordination status
- Confirmed, unconfirmed, or unavailable state
- Cross-border action cost

An unconfirmed interconnector request should never appear as equally executable beside a direct dispatch instruction.

## Metrics design rules

### Primary metrics

Keep these visible by default:

- Post-action security result
- Avoided dispatch-down waste
- Dispatch-down reduction
- Net financial value
- Earliest achievable execution

### Secondary metrics

Show, but with lower visual priority:

- Gross market opportunity
- Estimated avoided emissions

### Expanded-only metrics

Place these in details or evidence sections:

- Cost component breakdown
- Emissions-factor metadata
- Family-specific effectiveness metrics
- Payback or investment-recovery figures where supported by real asset data

Do not imply payback or investment recovery from avoided MWh alone.

## Carbon metric presentation

Estimated avoided emissions must be clearly labelled as a scenario estimate, not a verified carbon saving.

Display alongside the metric:

- Displaced generation assumption
- Emissions factor
- Unit
- Source
- Publication year
- Generic vs unit-specific factor
- Gross vs net treatment

For storage, where losses or rebound are known, show gross and net avoided-emissions values clearly.

## Ranking and recommendation UX

The frontend should explain why a recommendation was chosen in plain language.

For the selected action, show a short “why this action” panel with reasons such as:

- Keeps supported guardrails within modelled limits
- Avoids the most dispatch-down waste among secure options
- Delivers the strongest net value after applicable costs
- Can be executed before the deadline

For alternatives, show short rejection or lower-rank reasons such as:

- Breach after action
- Lower avoided waste
- Misses execution timing
- Higher cost for similar relief
- Coordination not confirmed

Avoid exposing a meaningless raw optimisation score if it does not help the operator act.

## State and status design

Use explicit system states everywhere.

Allowed guardrail and security states:

- within_modelled_limit
- breach
- unknown

Visual rules:

- Green for within_modelled_limit
- Red for breach
- Neutral or amber for unknown

Do not replace unknown with reassuring wording like “safe” or “clear.”

## Interaction rules

- Show one primary recommended action at a time
- Keep comparison visible without extra clicks
- Put detail behind expansion, not on separate screens where avoidable
- Use plain-language instructions for actions
- Make timestamps, units, and status labels consistent everywhere
- Prioritise scan speed over visual decoration

## Responsive behaviour

Desktop:

- Side-by-side baseline vs recommended comparison
- Persistent scenario list or context rail where space allows
- Expandable right-side detail panel

Tablet and mobile:

- Stack baseline and post-action cards vertically
- Collapse secondary detail into accordions
- Keep the recommended action card pinned near the top
- Preserve readability of timestamps, units, and status chips

This product should remain usable on smaller screens, but the primary design target is operational desktop use.

## Suggested component structure

- `ScenarioWorkspace`
- `ScenarioHeader`
- `ScenarioList`
- `BindingConditionCard`
- `RecommendedActionCard`
- `OutcomeComparisonPanel`
- `GuardrailStrip`
- `AlternativeActionsPanel`
- `AssumptionsAccordion`
- `EngineeringEvidenceAccordion`
- `WhyThisActionPanel`
- `ActionDetailsGeneratorSetpoint`
- `ActionDetailsCommitmentChange`
- `ActionDetailsStorageCharging`
- `ActionDetailsReactiveControl`
- `ActionDetailsRenewableLimit`
- `ActionDetailsInterconnectorRequest`

## Implementation phases

### Phase 1: Layout foundation

Build:

- App shell
- Scenario list
- Main scenario workspace layout
- Shared metric cards
- Guardrail strip
- Recommended action card shell

### Phase 2: Action-detail modules

Build all core action-family detail components.

Priority order:

1. Generator MW setpoint
2. Commitment change
3. Storage charging
4. Voltage/reactive control
5. Renewable limit
6. Interconnector request

### Phase 3: Evidence and alternatives

Add:

- Assumptions panel
- Alternatives ranking panel
- Cost breakdowns
- Carbon assumptions panel
- Unknown-state handling

### Phase 4: Reliability and polish

Add:

- Loading states
- Empty states
- Error states for incomplete model outputs
- Accessibility pass
- Responsive cleanup
- Formatting utilities for EUR, MWh, tCO2e, %, and timestamps

## Definition of done

The frontend is good enough for MVP when it can do the following cleanly:

- Show one scenario with a recommended action in a single readable workspace
- Compare baseline vs recommended action without confusion
- Make security status obvious before value metrics
- Present a complete operator instruction for every recommendation
- Explain why this action was selected and why others were not
- Handle unknown values honestly
- Keep assumptions and evidence accessible without cluttering the default view

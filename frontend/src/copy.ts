// All scope labels and caveats live here so the national forecast and the
// TYTFS planning scenario are named the same way in every state, and so the
// smoke test can check that copy never overclaims.

export const COPY = {
  appTitle: 'Scenario decision workspace',
  appPhase: 'Prototype',
  teamName: 'Team Blue',
  eventName: 'Hack the Climate 2026',
  liveBanner: 'Point-in-time input gated; no safe action recommendation without complete evidence.',

  forecastTitle: 'National forecast',
  forecastKind: 'Statistical forecast',
  forecastScope: 'All-Ireland constraint MWh and event risk, 1–24 hours ahead',
  forecastCaveat:
    'Forecasts the national constraint total only, separate from system-wide curtailment. The labels it learns from are national totals, so it does not identify a line, wind farm, node or constraint group.',
  forecastLoading: 'Loading national forecast…',
  contextTitle: 'Inputs available at decision time',

  scenarioTitle: 'TYTFS planning scenario',
  scenarioKind: 'Planning model',
  scenarioScope: 'Modelled intact vs planned-outage vs selected N-1 comparison on a 2024 planning case',
  scenarioCaveat:
    'DC flows from a Ten Year Transmission Forecast Statement (TYTFS) 2024 planning case, not the 2026 operating network. Loading and headroom are screening proxies, not measured or future operational flows. The selected N-1 run is one study case, not an operational security assessment.',
  scenarioLoading: 'Loading TYTFS planning scenario…',

  forecastConfidence: 'Forecast confidence',
  assetMatchConfidence: 'Asset match',

  notAvailable: 'Not available',
  fixtureBanner: 'Offline sample: workspace scenarios are illustrative, with invented values. Not served by the API yet.',
} as const;

// Consequence-led state messages: what the operator can and cannot rely on.
export const STATE_COPY = {
  forecastUnavailableTitle: 'No national outlook yet',
  forecastUnavailableConsequence:
    'This screen cannot show when national constraint risk rises. The planning scenario below still works, but it says nothing about timing.',
  forecastLoadingConsequence: 'Fetching the latest national forecast. Nothing is shown until it arrives.',
  forecastErrorTitle: 'National forecast did not load',
  forecastErrorConsequence: 'No forecast figures are shown, so none of them can be out of date. Try again, or check that the API is running.',
  forecastStaleTitle: 'Some forecast inputs are out of date',
  forecastStaleConsequence: 'Treat the timeline as less reliable until these sources refresh:',
  scenarioEmptyTitle: 'No outage selected',
  scenarioEmptyConsequence:
    'Pick a reviewed outage above to see how switching that equipment off would move power in the 2024 planning model.',
  scenarioLoadingConsequence: 'Solving the planning model for this outage.',
  scenarioErrorTitle: 'Planning scenario did not load',
  scenarioErrorConsequence: 'No modelled flows are shown for this outage. Try again, or pick another outage.',
  scenarioUnavailableTitle: 'This outage cannot be modelled yet',
  scenarioUnavailableConsequence:
    'No flow change is shown because the equipment could not be matched to the planning model with enough confidence.',
  retry: 'Try again',
  independence: 'The planning scenario does not change the national forecast. They answer separate questions.',
} as const;

// Scenario workspace (UX plan phase 1).
export const WORKSPACE_COPY = {
  advisory: 'Advisory',
  advisoryNote: 'Recommends an operator instruction. Does not send instructions to assets.',
  illustrative: 'Illustrative',
  illustrativeNote: 'Illustrative scenario: invented values for layout. Not a model result.',
  live: 'Solver result',
  situationLabel: 'Describe the situation',
  situationHint: 'Name the area, asset, limit and time, or ask for dispatch-down risk. The workspace returns the recommended next action or the risk estimate.',
  situationSubmit: 'Find next action',
  situationPlaceholder: 'e.g. line overload in the west after the outage',
  solvingTitle: 'Finding the next action…',
  solvingConsequence: 'No action is shown until the result arrives.',
  noMatchTitle: 'No scenario found for this description',
  noMatchConsequence: 'No action is shown. Add the area, asset or limit and try again.',
  solverUnavailableTitle: 'Scenario solver not connected',
  solverUnavailableConsequence: 'No action can be returned yet. Questions about dispatch-down risk still work. Use fixture mode to preview the workspace layout.',
  solverErrorTitle: 'Scenario solver did not respond',
  solverErrorConsequence: 'No action is shown. Try again.',
  clarifyTitle: 'The solver needs more detail',
  clarifyRound: 'Round',
  clarifyDescribed: 'You described',
  clarifyOptional: 'optional',
  clarifyNotSet: 'Not set',
  clarifyClear: 'Clear',
  clarifySubmit: 'Send answers',
  clarifyNext: 'Next',
  clarifySkip: 'Skip',
  clarifyBack: 'Back',
  clarifyQuestion: 'Question',
  clarifyOf: 'of',
  clarifyCancel: 'Start again',
  comparisonLabel: 'Compare',
  comparisonBaseline: 'Baseline vs recommended action',
  lastModelRun: 'Last model run',
  timeZoneNote: 'All times UTC',
  bindingTitle: 'Binding condition',
  bindingNone: 'No binding condition identified',
  actionTitle: 'Recommended action',
  actionNone: 'No recommended action',
  actionDetailsSummary: 'Action details',
  actionCostsTitle: 'Costs',
  interconnectorNotConfirmed:
    'Counterparty has not confirmed this request. It is not executable as a direct dispatch instruction.',
  outcomeTitle: 'New outcome',
  baseline: 'Baseline',
  postAction: 'Post-action',
  guardrailTitle: 'Guardrails',
  assistantTitle: 'Grid assistant',
  assistantRecommended: 'Recommended action',
  assistantToolsUsed: 'Data used',
  assistantNoTools: 'No tools called',
  assistantNote: 'Answers come only from the tools listed. Historical replays and experimental forecasts are labelled; check before acting.',
  traceTitle: 'How the assistant answered',
  traceSummary: 'Path through the LangGraph for this reply',
  traceSkipped: 'Not used this time',
} as const;

export const GUARDRAIL_STATUS_LABEL = {
  within_modelled_limit: 'Within modelled limit',
  breach: 'Breach',
  unknown: 'Unknown',
} as const;

export const GUARDRAIL_LABEL = {
  voltage: 'Voltage',
  thermal: 'Thermal capacity',
  snsp: 'SNSP',
  inertia: 'Inertia',
  frequency: 'Frequency',
} as const;

export const ACTION_FAMILY_LABEL = {
  generator_setpoint: 'Generator active-power output',
  commitment_change: 'Commitment state change',
  storage_charging: 'Storage charging',
  reactive_control: 'Voltage or reactive-power control',
  renewable_limit: 'Renewable active-power limit',
  interconnector_request: 'Interconnector flow change',
} as const;

export const EXECUTABILITY_LABEL = {
  executable: 'Executable',
  conditional: 'Conditional',
  unconfirmed: 'Unconfirmed',
} as const;

export const COORDINATION_LABEL = {
  confirmed: 'Confirmed',
  unconfirmed: 'Unconfirmed',
  unavailable: 'Unavailable',
} as const;

export const COMMITMENT_LABEL = {
  online: 'Online',
  offline: 'Offline',
} as const;

export const THERMAL_STATE_LABEL = {
  hot: 'Hot',
  warm: 'Warm',
  cold: 'Cold',
} as const;

// Plain-language definitions shown in tooltips.
export const GLOSSARY = {
  constraint:
    'Wind or solar output EirGrid reduces because the network cannot carry it in that area. Measured here as a national total in MWh.',
  eventProbability: 'The model’s chance that national constraint in that half-hour exceeds the event threshold.',
  horizon: 'How far ahead of the decision time the half-hour is. The forecast only uses information available at the decision time.',
  confidence:
    'How well the forecast did on past months it had not seen, tested in time order. It says nothing about the network scenario.',
  prAuc: 'A score from 0 to 1 for how well the model ranks risky half-hours above quiet ones. Compare it with event prevalence: rare events make high scores harder.',
  calibration: 'Whether a 70% chance really happens about 70% of the time in past data.',
  intervalCoverage: 'How often the real value fell inside the shaded uncertainty range in past data, compared with the target.',
  tytfs:
    'Ten Year Transmission Forecast Statement: EirGrid’s published planning model of the network. This one is a summer 2024 study case, not today’s grid.',
  plannedOutage: 'Equipment EirGrid has scheduled to switch off for work. A schedule does not prove it was actually off on a given day.',
  nMinusOne: 'One extra piece of equipment switched off on top of the planned outage, to test how the network copes. Chosen for study; not a published outage.',
  dcFlow: 'A simplified power-flow calculation. It ignores voltage, reactive power and losses, so results are approximate.',
  flowSize: 'How much active power the model sends along the monitored branch, ignoring direction.',
  loading: 'Modelled flow as a share of the branch’s rate A rating. A screening figure, not measured thermal loading.',
  headroom: 'Rate A minus modelled flow: how much more the branch could carry in the model before reaching its rating.',
  rateA: 'The branch’s normal continuous rating in the planning case, in MVA.',
  assetMatch:
    'How sure we are that the outage in EirGrid’s outage list and the equipment in the planning model are the same thing. Separate from forecast confidence.',
  loadingBand: 'Display bands used on this screen: under 80% normal, 80–100% caution, over 100% critical. They are not EirGrid operating limits.',
} as const;

// Phrases the UI must never show. Checked by the smoke test.
export const FORBIDDEN_PHRASES = [
  'will be constrained',
  'will constrain',
  'actual loading',
  'actual future loading',
  'guaranteed',
  'real-time flow',
  'binding line',
  'binding constraint group',
  'affected wind farm',
  'n-1 secure',
  'passes n-1',
  'fails n-1',
  'curtailment forecast',
  'grid safe',
  'optimised outcome',
  'high-impact',
  'best action',
];

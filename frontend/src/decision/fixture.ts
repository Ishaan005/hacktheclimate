// Offline sample assessment for layout work and tests. Invented values on a
// named demonstration case; never shown as live. Source kind is
// 'historical_demo' and validated is false, so no badge reads as a live,
// validated result.

import type { Assessment, Established } from './types';

const WINDOW_START = '2026-01-24T16:00:00Z';
const WINDOW_END = '2026-01-24T18:00:00Z';

function notEstablished(unit: string, reason: string): Established {
  return { value: null, lower: null, upper: null, unit, method: null, source: null, notEstablishedReason: reason };
}

function estimate(value: number, lower: number | null, upper: number | null, unit: string, method: string, source: string): Established {
  return { value, lower, upper, unit, method, source, notEstablishedReason: null };
}

export const fixtureAssessment: Assessment = {
  validated: false,
  context: {
    view: 'national',
    location: 'All-island',
    siteId: null,
    siteConnection: null,
    limitingRoute: 'Cashla–Flagford 220 kV',
    currentTime: '2026-01-24T15:40:00Z',
    windowStart: WINDOW_START,
    windowEnd: WINDOW_END,
    sourceKind: 'historical_demo',
    dataStatus: 'stale',
  },
  conditions: [
    {
      scenarioId: 'T3',
      situationKey: 't_outage_overload',
      reach: 'shared_route',
      limitingAsset: 'Cashla–Flagford 220 kV line',
      outageType: 'planned',
      timeSetting: 'forecast',
      snspDrivers: [],
      jurisdiction: null,
      confirmedByOperator: false,
    },
    {
      scenarioId: 'SNSP',
      situationKey: 'snsp_limit',
      reach: null,
      limitingAsset: null,
      outageType: null,
      timeSetting: 'forecast',
      snspDrivers: ['renewables_up', 'demand_down'],
      jurisdiction: null,
      confirmedByOperator: false,
    },
  ],
  causeUnknown: null,
  facts: [
    { id: 'outage_equipment', label: 'Outage equipment', value: 'Cashla–Tynagh 220 kV', unit: null, source: 'Annual outage programme 2026', timestamp: '2026-01-20T09:00:00Z', origin: 'measured', state: 'current', family: 'transmission', conflictNote: null, editable: false, editedFrom: null },
    { id: 'studied_flow', label: 'Studied flow on limiting route', value: 438, unit: 'MW', source: 'TYTFS 2024 planning case (DC)', timestamp: '2026-01-24T15:30:00Z', origin: 'forecast', state: 'current', family: 'transmission', conflictNote: null, editable: true, editedFrom: null },
    { id: 'actual_flow', label: 'Actual flow on limiting route', value: null, unit: 'MW', source: null, timestamp: null, origin: 'measured', state: 'missing', family: 'transmission', conflictNote: null, editable: true, editedFrom: null },
    { id: 'route_rating', label: 'Route rating (winter)', value: 431, unit: 'MVA', source: 'TYTFS 2024 rating table', timestamp: '2024-06-01T00:00:00Z', origin: 'measured', state: 'stale', family: 'transmission', conflictNote: null, editable: true, editedFrom: null },
    { id: 'credible_failure', label: 'Credible failure set', value: 'Flagford–Srananagh 220 kV', unit: null, source: 'Operator', timestamp: '2026-01-24T15:35:00Z', origin: 'operator', state: 'current', family: 'transmission', conflictNote: null, editable: true, editedFrom: null },
    { id: 'wind_output', label: 'Wind output', value: 3920, unit: 'MW', source: 'EirGrid system data', timestamp: '2026-01-24T15:30:00Z', origin: 'measured', state: 'current', family: 'snsp', conflictNote: null, editable: false, editedFrom: null },
    { id: 'solar_output', label: 'Solar output', value: 0, unit: 'MW', source: 'EirGrid system data', timestamp: '2026-01-24T15:30:00Z', origin: 'measured', state: 'current', family: 'snsp', conflictNote: null, editable: false, editedFrom: null },
    { id: 'demand', label: 'All-island demand', value: 5210, unit: 'MW', source: 'EirGrid system data', timestamp: '2026-01-24T15:30:00Z', origin: 'measured', state: 'current', family: 'snsp', conflictNote: null, editable: false, editedFrom: null },
    { id: 'net_imports', label: 'Net interconnector transfer (+import)', value: 450, unit: 'MW', source: 'EirGrid system data', timestamp: '2026-01-24T15:30:00Z', origin: 'measured', state: 'conflicting', family: 'snsp', conflictNote: 'Interconnector schedule shows +250 MW.', editable: true, editedFrom: null },
    { id: 'snsp_limit', label: 'Effective SNSP limit', value: 75, unit: '%', source: 'Operational policy roadmap', timestamp: '2025-10-01T00:00:00Z', origin: 'inferred', state: 'current', family: 'snsp', conflictNote: null, editable: true, editedFrom: null },
    { id: 'stability_results', label: 'Inertia and RoCoF study', value: null, unit: null, source: null, timestamp: null, origin: 'measured', state: 'missing', family: 'snsp', conflictNote: null, editable: true, editedFrom: null },
  ],
  activeInstructions: [
    { id: 'ai-1', text: 'Wind group WDT limit 180 MW', asset: 'North-west wind group', issuedAt: '2026-01-24T14:50:00Z', effectiveUntil: '2026-01-24T18:00:00Z', source: 'Demonstration dispatch log' },
  ],
  edits: [],
  overall: {
    result: 'unknown',
    reason: 'Worst post-failure flow and stability study are missing, so the combination cannot be shown safe.',
    missingEvidence: ['Actual flow on limiting route', 'Inertia and RoCoF study', 'Protection check for switching sequence'],
  },
  familyChecks: [
    { id: 'fc-flow', label: 'Flow versus rating on limiting route', family: 'transmission', value: '406 MW', limit: '431 MVA', margin: '+25 MW', worstTime: '2026-01-24T17:00:00Z', worstFailure: null, source: 'TYTFS 2024 planning case (DC)', result: 'pass', reason: 'With the plan, studied flow stays below the winter rating. The rating table is stale.' },
    { id: 'fc-n1', label: 'Worst flow after one further failure', family: 'transmission', value: null, limit: '431 MVA', margin: null, worstTime: null, worstFailure: 'Flagford–Srananagh 220 kV', source: null, result: 'unknown', reason: 'No study for the further failure during this outage.' },
    { id: 'fc-relief', label: 'Relief arrives before breach', family: 'transmission', value: '20 min', limit: '35 min to breach', margin: '15 min', worstTime: '2026-01-24T16:35:00Z', worstFailure: null, source: 'Demonstration timing', result: 'pass', reason: 'Relief is expected before the forecast breach.' },
    { id: 'fc-snsp', label: 'All-island SNSP margin', family: 'snsp', value: '72.4%', limit: '75%', margin: '2.6 pts', worstTime: '2026-01-24T17:30:00Z', worstFailure: null, source: 'Derived from EirGrid system data', result: 'pass', reason: 'Below the effective limit at the worst time.' },
    { id: 'fc-stability', label: 'Inertia and RoCoF', family: 'snsp', value: null, limit: null, margin: null, worstTime: null, worstFailure: null, source: null, result: 'unknown', reason: 'No stability study attached. A safe SNSP percentage alone does not prove stability.' },
  ],
  crossChecks: [
    { id: 'cc-battery-ffr', label: 'Battery headroom promised for frequency service', family: 'cross_family', value: '12 MW', limit: '10 MW reserved', margin: '2 MW', worstTime: '2026-01-24T17:00:00Z', worstFailure: null, source: 'Demonstration asset register', result: 'pass', reason: 'Charging leaves the promised response headroom.' },
  ],
  actionChecks: [
    { id: 'ac-redispatch-match', stepId: 'step-1', goNoGo: true, label: 'Matched MW at each step', family: 'transmission', value: '−40 / +40 MW', limit: 'Balanced', margin: '0 MW', worstTime: null, worstFailure: null, source: 'Demonstration dispatch', result: 'pass', reason: 'Decrease and increase are matched.' },
    { id: 'ac-redispatch-range', stepId: 'step-1', goNoGo: false, label: 'Unit range and ramp', family: 'transmission', value: '4 MW/min', limit: '2 MW/min needed', margin: '2 MW/min', worstTime: null, worstFailure: null, source: 'Demonstration asset register', result: 'pass', reason: 'Both units can ramp in time.' },
    { id: 'ac-storage-relief', stepId: 'step-2', goNoGo: true, label: 'Metered relief behind the bottleneck', family: 'transmission', value: '15 MW', limit: null, margin: null, worstTime: null, worstFailure: null, source: null, result: 'unknown', reason: 'No meter confirms the battery sits behind the limiting route.' },
    { id: 'ac-storage-energy', stepId: 'step-2', goNoGo: false, label: 'Available energy and rebound', family: 'transmission', value: '30 MWh room', limit: '30 MWh over 2 h', margin: '0 MWh', worstTime: '2026-01-24T18:00:00Z', worstFailure: null, source: 'Demonstration asset register', result: 'pass', reason: 'Room to charge covers the window; rebound after 18:00 not studied.' },
  ],
  allIslandChecks: [
    { id: 'ai-snsp', label: 'All-island SNSP margin', family: 'snsp', value: '72.4%', limit: '75%', margin: '2.6 pts', worstTime: '2026-01-24T17:30:00Z', worstFailure: null, source: 'Derived from EirGrid system data', result: 'pass', reason: 'Below the effective limit.' },
  ],
  proposed: {
    id: 'plan-proposed',
    name: 'Paired redispatch with local battery charging',
    origin: 'proposed',
    label: 'conditional',
    labelReason: 'Generator owner acceptance is pending.',
    steps: [
      { id: 'step-1', kind: 'paired_redispatch', role: 'main', instruction: 'Reduce Wind Farm A by 40 MW; increase Tynagh CCGT by 40 MW.', executor: 'Wind Farm A / Tynagh CCGT', permissionRoute: 'needs_acceptance', permissionState: 'pending', permissionParty: 'Tynagh generator owner', startTime: '2026-01-24T16:00:00Z', effectTime: '2026-01-24T16:20:00Z', durationMinutes: 120, mwEffect: -32, dependsOn: [], blockingCheckIds: [] },
      { id: 'step-2', kind: 'local_storage_or_demand', role: 'supporting', instruction: 'Charge Battery B at 15 MW.', executor: 'Battery B', permissionRoute: 'direct', permissionState: 'confirmed', permissionParty: null, startTime: '2026-01-24T16:05:00Z', effectTime: '2026-01-24T16:07:00Z', durationMinutes: 120, mwEffect: -12, dependsOn: ['step-1'], blockingCheckIds: ['ac-storage-relief'] },
    ],
  },
  alternative: null,
  outcomes: [
    {
      column: 'current', available: true, unavailableReason: null, windowStart: WINDOW_START, windowEnd: WINDOW_END, includesActiveInstructions: true,
      safety: 'fail', worstMargin: '−7 MW',
      deliveredReliefMw: estimate(0, null, null, 'MW', 'No new relief', 'Demonstration'),
      responseTimeMinutes: notEstablished('min', 'No new instruction.'),
      timeToBreachMinutes: estimate(35, 25, 50, 'min', 'Planning-case flow trend', 'TYTFS 2024 (DC)'),
      constrainedMwh: estimate(48, 30, 70, 'MWh', 'Planning-case replay', 'Demonstration'),
      curtailedMwh: notEstablished('MWh', 'No curtailment model for this window.'),
    },
    {
      column: 'no_new_instruction', available: true, unavailableReason: null, windowStart: WINDOW_START, windowEnd: WINDOW_END, includesActiveInstructions: true,
      safety: 'fail', worstMargin: '−19 MW',
      deliveredReliefMw: estimate(0, null, null, 'MW', 'No new relief', 'Demonstration'),
      responseTimeMinutes: notEstablished('min', 'No new instruction.'),
      timeToBreachMinutes: estimate(35, 25, 50, 'min', 'Planning-case flow trend', 'TYTFS 2024 (DC)'),
      constrainedMwh: estimate(40, 30, 50, 'MWh', 'Planning-case replay', 'Demonstration'),
      curtailedMwh: notEstablished('MWh', 'No curtailment model for this window.'),
    },
    {
      column: 'proposed', available: true, unavailableReason: null, windowStart: WINDOW_START, windowEnd: WINDOW_END, includesActiveInstructions: true,
      safety: 'unknown', worstMargin: '+25 MW',
      deliveredReliefMw: estimate(44, 30, 44, 'MW', 'Step MW effects at limiting route', 'Demonstration'),
      responseTimeMinutes: estimate(20, 15, 25, 'min', 'Declared ramp', 'Demonstration asset register'),
      timeToBreachMinutes: notEstablished('min', 'No breach expected if relief arrives; further-failure study missing.'),
      constrainedMwh: estimate(20, 10, 30, 'MWh', 'Planning-case replay', 'Demonstration'),
      curtailedMwh: notEstablished('MWh', 'No curtailment model for this window.'),
    },
    {
      column: 'operator_alternative', available: false, unavailableReason: 'No operator alternative entered.', windowStart: WINDOW_START, windowEnd: WINDOW_END, includesActiveInstructions: true,
      safety: 'unknown', worstMargin: null,
      deliveredReliefMw: notEstablished('MW', 'No operator alternative entered.'),
      responseTimeMinutes: notEstablished('min', 'No operator alternative entered.'),
      timeToBreachMinutes: notEstablished('min', 'No operator alternative entered.'),
      constrainedMwh: notEstablished('MWh', 'No operator alternative entered.'),
      curtailedMwh: notEstablished('MWh', 'No operator alternative entered.'),
    },
  ],
  benefits: {
    avoidedDispatchDownMwh: { ...estimate(20, 0, 40, 'MWh', 'No-new-instruction minus proposed, planning-case replay', 'Demonstration'), notEstablishedReason: null },
    siteRiskProbability: notEstablished('%', 'No validated site model.'),
    siteRiskExpectedMwh: notEstablished('MWh', 'No validated site model.'),
    nationalContext: 'Experimental national constraint forecast: context only, not a site outcome.',
    netSystemResourceCostEur: { ...notEstablished('EUR', 'Dispatch and activation prices not supplied.'), perspective: 'TSO system cost' },
    grossMarketOpportunityEur: notEstablished('EUR', 'Route, product and price not known.'),
    netFinancialValueEur: { ...notEstablished('EUR', 'No agreed revenue or avoided cost.'), perspective: null },
    carbonEffectTco2e: notEstablished('tCO2e', 'Displaced generation is not modelled.'),
  },
  evidence: {
    inputs: [
      { label: 'Studied flow on limiting route', source: 'TYTFS 2024 planning case (DC)', timestamp: '2026-01-24T15:30:00Z', editedByOperator: false },
      { label: 'Wind output', source: 'EirGrid system data', timestamp: '2026-01-24T15:30:00Z', editedByOperator: false },
      { label: 'Credible failure set', source: 'Operator', timestamp: '2026-01-24T15:35:00Z', editedByOperator: true },
    ],
    ruleVersion: 'demo-policy-v1 (not EirGrid/SONI confirmed)',
    modelVersions: ['TYTFS 2024 DC planning case', 'GFS national constraint (experimental)'],
    limitsUsed: ['Winter rating 431 MVA', 'SNSP 75%'],
    credibleFailuresUsed: ['Flagford–Srananagh 220 kV'],
    actionDecisions: [
      { stepId: 'step-1', kind: 'paired_redispatch', decision: 'conditional', reason: 'Largest relief at the limiting route; waits for generator owner acceptance.' },
      { stepId: 'step-2', kind: 'local_storage_or_demand', decision: 'included', reason: 'Adds relief; metered location still unconfirmed.' },
      { stepId: null, kind: 'switch_sectionalise', decision: 'rejected', reason: 'No protection or fault-current study for the switching sequence.' },
    ],
    assumptions: ['Planning-case flows stand in for operational flows.', 'Battery B is behind the limiting route.'],
    uncertainty: ['Avoided dispatch-down range 0–80 MWh.'],
    missingChecks: ['Further-failure study during outage', 'Inertia and RoCoF study'],
    assessedAt: '2026-01-24T15:41:00Z',
    auditId: 'demo-0001',
    feedFreshness: [
      { feed: 'EirGrid system data', status: 'current', asOf: '2026-01-24T15:30:00Z' },
      { feed: 'Rating table', status: 'stale', asOf: '2024-06-01T00:00:00Z' },
      { feed: 'SCADA', status: 'missing', asOf: null },
    ],
  },
};

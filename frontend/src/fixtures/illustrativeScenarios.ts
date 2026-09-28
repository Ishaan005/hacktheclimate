// ILLUSTRATIVE scenarios for workspace layout work and UI tests only.
//
// Unlike operatorView.ts, every value here is invented. Asset names are
// placeholders ("Generator A"), not EirGrid units, and no number comes from a
// model run. The UI labels these scenarios as illustrative in every state.
// Live mode maps /v1/operator/view instead (see src/scenarios.ts).

import type { Guardrail, GuardrailName, GuardrailStatus, WorkspaceScenario } from '../types';

function guardrail(
  name: GuardrailName,
  baseline: GuardrailStatus,
  postAction: GuardrailStatus,
  margin: string | null = null,
  timestamp: string | null = null,
  note: string | null = null,
): Guardrail {
  return { name, baseline, postAction, margin, timestamp, note };
}

export const illustrativeScenarios: WorkspaceScenario[] = [
  {
    id: 'illustrative-thermal-west',
    title: 'West 110 kV corridor overload',
    intervalStart: '2026-09-29T15:00:00Z',
    intervalEnd: '2026-09-29T16:30:00Z',
    source: 'illustrative',
    modelRunAt: '2026-09-29T14:45:00Z',
    summary: 'High wind in the west loads Line W-1 above its modelled thermal limit after a planned outage.',
    keywords: ['wind', 'west', 'line', 'overload', 'thermal', 'outage', 'corridor', 'loading'],
    binding: {
      type: 'Thermal capacity',
      metric: 'Line W-1 loading 104% of rating',
      location: 'West 110 kV corridor',
      margin: '−6 MW to limit',
      status: 'breach',
    },
    action: {
      family: 'generator_setpoint',
      assetName: 'Generator A',
      location: 'East 220 kV node',
      currentState: '60 MW',
      targetState: '100 MW',
      issueTime: '2026-09-29T14:55:00Z',
      startTime: '2026-09-29T15:00:00Z',
      targetTime: '2026-09-29T15:10:00Z',
      effectiveUntil: '2026-09-29T16:30:00Z',
      earliestExecution: '2026-09-29T15:00:00Z',
      executability: 'executable',
    },
    noActionReason: null,
    baseline: { securityResult: 'breach', dispatchDownWasteMwh: 42 },
    postAction: { securityResult: 'within_modelled_limit', dispatchDownWasteMwh: 12 },
    impact: {
      grossMarketOpportunityEur: 3150,
      netFinancialValueEur: 1900,
      estimatedAvoidedEmissionsTco2e: 11.4,
    },
    guardrails: [
      guardrail('voltage', 'within_modelled_limit', 'within_modelled_limit', '0.03 pu', '2026-09-29T15:00:00Z'),
      guardrail('thermal', 'breach', 'within_modelled_limit', '+18 MW', '2026-09-29T15:10:00Z'),
      guardrail('snsp', 'within_modelled_limit', 'within_modelled_limit', '6 pp'),
      guardrail('inertia', 'within_modelled_limit', 'within_modelled_limit', '4,200 MWs'),
      guardrail('frequency', 'unknown', 'unknown', null, null, 'No RoCoF study attached.'),
    ],
  },
  {
    id: 'illustrative-voltage-north',
    title: 'North-west low voltage at evening ramp',
    intervalStart: '2026-09-29T17:30:00Z',
    intervalEnd: '2026-09-29T19:00:00Z',
    source: 'illustrative',
    modelRunAt: '2026-09-29T14:45:00Z',
    summary: 'Evening demand ramp pulls North-west 110 kV voltage towards its lower limit.',
    keywords: ['voltage', 'north', 'evening', 'ramp', 'reactive', 'demand', 'low'],
    binding: {
      type: 'Voltage',
      metric: 'Bus NW-3 voltage 0.91 pu',
      location: 'North-west 110 kV',
      margin: '0.01 pu to limit',
      status: 'within_modelled_limit',
    },
    action: {
      family: 'storage_charging',
      assetName: 'Storage B',
      location: 'North-west 110 kV node',
      currentState: 'idle at 40% state of charge',
      targetState: 'charging at 20 MW',
      issueTime: '2026-09-29T17:10:00Z',
      startTime: '2026-09-29T17:20:00Z',
      targetTime: '2026-09-29T17:30:00Z',
      effectiveUntil: '2026-09-29T19:00:00Z',
      earliestExecution: '2026-09-29T17:20:00Z',
      executability: 'executable',
    },
    noActionReason: null,
    baseline: { securityResult: 'within_modelled_limit', dispatchDownWasteMwh: 0 },
    postAction: { securityResult: 'unknown', dispatchDownWasteMwh: 0 },
    impact: {
      grossMarketOpportunityEur: 600,
      netFinancialValueEur: -150,
      estimatedAvoidedEmissionsTco2e: null,
    },
    guardrails: [
      guardrail('voltage', 'within_modelled_limit', 'unknown', null, '2026-09-29T17:30:00Z', 'Post-charge voltage not studied.'),
      guardrail('thermal', 'within_modelled_limit', 'within_modelled_limit', '+55 MW'),
      guardrail('snsp', 'within_modelled_limit', 'within_modelled_limit', '9 pp'),
      guardrail('inertia', 'within_modelled_limit', 'within_modelled_limit', '5,100 MWs'),
      guardrail('frequency', 'unknown', 'unknown', null, null, 'No RoCoF study attached.'),
    ],
  },
  {
    id: 'illustrative-snsp-night',
    title: 'Overnight SNSP ceiling',
    intervalStart: '2026-09-30T02:00:00Z',
    intervalEnd: '2026-09-30T05:00:00Z',
    source: 'illustrative',
    modelRunAt: '2026-09-29T14:45:00Z',
    summary: 'Low overnight demand and high wind push system non-synchronous penetration to its ceiling.',
    keywords: ['snsp', 'night', 'overnight', 'wind', 'demand', 'synchronous', 'penetration', 'ceiling'],
    binding: {
      type: 'SNSP',
      metric: 'SNSP 75% of 75% ceiling',
      location: 'All-island system',
      margin: '0 pp to limit',
      status: 'within_modelled_limit',
    },
    action: null,
    noActionReason: 'No loaded action keeps every supported guardrail within modelled limits for this interval.',
    baseline: { securityResult: 'within_modelled_limit', dispatchDownWasteMwh: 88 },
    postAction: null,
    impact: null,
    guardrails: [
      guardrail('voltage', 'within_modelled_limit', 'unknown'),
      guardrail('thermal', 'within_modelled_limit', 'unknown'),
      guardrail('snsp', 'within_modelled_limit', 'unknown', '0 pp', '2026-09-30T03:00:00Z'),
      guardrail('inertia', 'within_modelled_limit', 'unknown', '1,100 MWs'),
      guardrail('frequency', 'unknown', 'unknown', null, null, 'No RoCoF study attached.'),
    ],
  },
];

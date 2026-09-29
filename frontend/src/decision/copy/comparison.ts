// Words for the outcome comparison and benefit cards (UI brief section 6).
// Plain operator language. Safety comes before energy and money.

import type { ComparisonColumn } from '../types';

export const COLUMN_ORDER: ComparisonColumn[] = ['current', 'no_new_instruction', 'proposed', 'operator_alternative'];

export const COLUMN_LABEL: Record<ComparisonColumn, string> = {
  current: 'Current plan',
  no_new_instruction: 'No new instruction',
  proposed: 'Proposed plan',
  operator_alternative: 'Operator alternative',
};

export const COMPARISON_COPY = {
  title: 'Compare outcomes',
  measure: 'Measure',
  baselineTag: 'Baseline for claimed improvements',
  window: (range: string) => `All columns cover ${range} UTC, including instructions already in force.`,
  mismatch: (columns: string) =>
    `Window mismatch: ${columns} use a different time window or leave out active instructions. Those columns are not comparable.`,
  notEvaluated: 'Not evaluated',
  safetyGroup: 'Safety and response',
  dispatchDownGroup: 'Remaining dispatch-down',
  rows: {
    safety: 'Safety result',
    worstMargin: 'Worst limit margin',
    deliveredRelief: 'Delivered relief (MW)',
    responseTime: 'Response time (min)',
    timeToBreach: 'Time to breach (min)',
    constrained: 'Constrained (MWh)',
    curtailed: 'Curtailed (MWh)',
  },
  noReason: 'No reason given.',
  method: 'Method',
  source: 'Source',
  range: 'Range',
};

export const BENEFIT_COPY = {
  title: 'Benefits of the proposed plan',
  cannotClaim: (result: string) => `Cannot be claimed: required safety check is ${result}`,
  contextOnly: 'Shown as context only.',
  cannotClaimNote: 'A plan with a failed or unknown safety check cannot win on benefits.',
  avoided: 'Avoided dispatch-down',
  avoidedDetail: 'No new instruction minus proposed plan.',
  avoidedNote: 'A MW × time upper bound is not proven saved energy.',
  siteRisk: 'Site dispatch-down risk',
  siteProbability: 'Probability',
  siteExpected: 'Expected energy',
  siteNationalView: 'National view: pick a site to see a site outcome.',
  nationalContext: 'National context only, not a site outcome',
  systemCost: 'Net system resource cost',
  marketOpportunity: 'Gross market opportunity',
  marketNote: 'Estimate, not TSO profit.',
  financialValue: 'Net financial value',
  financialNote: 'Kept separate from system resource cost.',
  carbon: 'Carbon effect',
  carbonNote: 'Recovered renewable power does not automatically reduce cost or carbon.',
  perspective: (perspective: string | null) => (perspective ? `Perspective: ${perspective}` : 'Perspective not stated'),
};

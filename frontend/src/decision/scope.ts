// Search suggestions from the locked scenario scope
// (config/decision_scenarios_v1.json). The screen shows the plain-language
// text; T1–T4 and H1–H4 stay internal IDs. Nothing outside this list can be
// suggested.

import type { Jurisdiction, ScenarioFamily, ScenarioId, SnspDriver, TransmissionReach } from './types';

export type Suggestion = {
  // Stable key, stored as BindingCondition.situationKey.
  key: string;
  scenarioId: ScenarioId;
  family: ScenarioFamily;
  text: string;
  // Words the plain-language matcher recognises.
  keywords: string[];
};

export const FAMILY_LABEL: Record<ScenarioFamily, string> = {
  transmission: 'Transmission constraint',
  high_frequency_minimum_generation: 'High frequency / minimum generation',
  snsp: 'SNSP',
};

export const SUGGESTIONS: Suggestion[] = [
  { key: 't_intact_overload', scenarioId: 'T1', family: 'transmission', text: 'A route is overloaded while all equipment is in service.', keywords: ['overload', 'overloaded', 'intact', 'all equipment', 'in service'] },
  { key: 't_intact_trip_risk', scenarioId: 'T2', family: 'transmission', text: 'The route is safe now, but one trip would overload it.', keywords: ['one trip', 'n-1', 'trip would', 'contingency', 'single failure'] },
  { key: 't_outage_overload', scenarioId: 'T3', family: 'transmission', text: 'A route is overloaded during an existing outage.', keywords: ['outage', 'overloaded during', 'out of service'] },
  { key: 't_outage_trip_risk', scenarioId: 'T4', family: 'transmission', text: 'The route is safe during an outage, but one further trip would overload it.', keywords: ['further trip', 'n-1-1', 'outage plus', 'during an outage'] },
  { key: 'h_lost_export', scenarioId: 'H1', family: 'high_frequency_minimum_generation', text: 'Measured high frequency after lost interconnector export.', keywords: ['high frequency', 'lost export', 'interconnector trip', 'hvdc trip'] },
  { key: 'h_demand_drop', scenarioId: 'H1', family: 'high_frequency_minimum_generation', text: 'Measured high frequency after a sudden demand drop.', keywords: ['high frequency', 'demand drop', 'load loss'] },
  { key: 'h_generation_rise', scenarioId: 'H1', family: 'high_frequency_minimum_generation', text: 'Measured high frequency after unexpected generation or import rise.', keywords: ['high frequency', 'generation rise', 'import rise'] },
  { key: 'h_min_units_ie', scenarioId: 'H2', family: 'high_frequency_minimum_generation', text: 'The minimum conventional units rule binds in Ireland.', keywords: ['minimum units', 'min gen', 'minimum generation', 'ireland'] },
  { key: 'h_min_units_ni', scenarioId: 'H2', family: 'high_frequency_minimum_generation', text: 'The minimum conventional units rule binds in Northern Ireland.', keywords: ['minimum units', 'min gen', 'northern ireland'] },
  { key: 'h_min_units_both', scenarioId: 'H2', family: 'high_frequency_minimum_generation', text: 'The minimum conventional units rule binds in both jurisdictions.', keywords: ['minimum units', 'min gen', 'both'] },
  { key: 'h_reserve_up', scenarioId: 'H3', family: 'high_frequency_minimum_generation', text: 'The upward reserve requirement binds.', keywords: ['reserve', 'upward reserve'] },
  { key: 'h_reserve_down', scenarioId: 'H3', family: 'high_frequency_minimum_generation', text: 'The downward reserve requirement binds, where the effective policy requires it.', keywords: ['downward reserve', 'negative reserve'] },
  { key: 'h_ramp_up', scenarioId: 'H4', family: 'high_frequency_minimum_generation', text: 'Power needs to rise over the coming window.', keywords: ['ramp', 'ramp up', 'upward ramp'] },
  { key: 'h_ramp_down', scenarioId: 'H4', family: 'high_frequency_minimum_generation', text: 'Power needs to fall over the coming window.', keywords: ['ramp down', 'downward ramp'] },
  { key: 'snsp_limit', scenarioId: 'SNSP', family: 'snsp', text: 'All-island SNSP is at or near its limit.', keywords: ['snsp', 'non-synchronous', 'penetration'] },
];

export const REACH_LABEL: Record<TransmissionReach, string> = {
  local_area: 'One local area',
  shared_route: 'Several areas sharing a route',
  wide_group: 'A wide renewable group',
};

export const SNSP_DRIVER_LABEL: Record<SnspDriver, string> = {
  renewables_up: 'More renewable output',
  demand_down: 'Less demand',
  imports_up: 'More imports',
  exports_down: 'Less exports',
};

// A forecast surplus with normal measured frequency is not a high-frequency
// event. It stays in intake until the limiting cause is known.
const FORECAST_SURPLUS = /\b(forecast|expected|predicted)\b.*\bsurplus\b|\bsurplus\b.*\b(forecast|expected)\b/i;
const MEASURED_HIGH_FREQUENCY = /\b(measured|actual|now)\b.*\bhigh frequency\b|\bhigh frequency\b.*\b(measured|now)\b|\b50\.[2-9]\d*\s*hz\b/i;

const OUTAGE = /\boutages?\b|out of service|\bn-1-1\b/;
const TRIP_RISK = /\btrip\b|\bn-1\b|contingency|single failure|further failure/;

function transmissionCondition(lower: string): ScenarioId | null {
  const outage = OUTAGE.test(lower);
  const tripRisk = TRIP_RISK.test(lower) && !/\boverloaded (now|during)\b/.test(lower);
  if (outage) return tripRisk ? 'T4' : 'T3';
  return tripRisk ? 'T2' : 'T1';
}

export type MatchResult =
  | { kind: 'matched'; suggestions: Suggestion[] }
  | { kind: 'cause_unknown'; reason: string; factsNeeded: string[] };

// Plain-language match against the locked scope only. Several suggestions
// can match; the operator reviews them before assessment.
export function matchDescription(text: string): MatchResult {
  const lower = text.toLowerCase();
  if (FORECAST_SURPLUS.test(lower) && !MEASURED_HIGH_FREQUENCY.test(lower)) {
    return {
      kind: 'cause_unknown',
      reason: 'A forecast surplus with normal measured frequency is not a high-frequency event.',
      factsNeeded: ['Measured frequency and time', 'Which requirement binds: minimum units, reserve or ramping', 'Effective policy'],
    };
  }
  const scored = SUGGESTIONS
    .map((suggestion) => ({ suggestion, score: suggestion.keywords.filter((word) => lower.includes(word)).length }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score);
  if (!scored.length) {
    return {
      kind: 'cause_unknown',
      reason: 'The description does not name a limiting cause in the locked scope.',
      factsNeeded: ['Limiting route or requirement', 'Measured or forecast value against its limit', 'Now or forecast, and the time window'],
    };
  }
  // Keep the best match per scenario so one scenario is not listed three times.
  const best = new Map<ScenarioId, Suggestion>();
  for (const { suggestion } of scored) {
    if (!best.has(suggestion.scenarioId)) best.set(suggestion.scenarioId, suggestion);
  }
  // One route is in exactly one of the four transmission conditions: an
  // existing outage and a further-trip risk decide which.
  const transmission = transmissionCondition(lower);
  const suggestions = [...best.values()].filter((suggestion) => suggestion.family !== 'transmission');
  if (transmission && [...best.values()].some((suggestion) => suggestion.family === 'transmission')) {
    const picked = SUGGESTIONS.find((suggestion) => suggestion.scenarioId === transmission);
    if (picked) suggestions.unshift(picked);
  }
  return { kind: 'matched', suggestions };
}

export function suggestionByKey(key: string | null): Suggestion | undefined {
  return SUGGESTIONS.find((suggestion) => suggestion.key === key);
}

export function familyOf(scenarioId: ScenarioId): ScenarioFamily {
  if (scenarioId === 'SNSP') return 'snsp';
  return scenarioId.startsWith('T') ? 'transmission' : 'high_frequency_minimum_generation';
}

// H2 has one suggestion per jurisdiction; the key and the choice must agree.
export const JURISDICTION_KEY: Record<Jurisdiction, string> = {
  ireland: 'h_min_units_ie',
  northern_ireland: 'h_min_units_ni',
  both: 'h_min_units_both',
};

export function jurisdictionOf(key: string): Jurisdiction | null {
  const match = (Object.keys(JURISDICTION_KEY) as Jurisdiction[]).find((item) => JURISDICTION_KEY[item] === key);
  return match ?? null;
}

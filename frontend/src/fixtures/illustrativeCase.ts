// ILLUSTRATIVE intake for fixture mode only. Live mode calls POST /v1/intake.
//
// A description that matches an illustrative scenario gets that scenario's
// invented values as facts, labelled as illustrative. Anything else gets an
// empty case, so every required fact is asked for.

import { newCase } from '../case';
import { resolveSituation } from '../scenarios';
import type { CaseAction, CaseActionFamily, Fact, FactValue, OperatorCase, ScenarioFamily } from '../case';
import type { WorkspaceScenario } from '../types';

const FAMILY_PATTERNS: [CaseActionFamily, RegExp][] = [
  ['outage_review', /\b(reschedul\w*|move the outage|outage review|review the outage)\b/i],
  ['storage_charging', /\b(battery|storage|pumped)\b/i],
  ['flexible_demand', /\b(flexible demand|demand response|data cent(re|er)|workload|ev charging)\b/i],
  ['generator_redispatch', /\b(generator|redispatch|unit output)\b/i],
];

export function detectActionFamily(text: string): CaseActionFamily | null {
  return FAMILY_PATTERNS.find(([, pattern]) => pattern.test(text))?.[0] ?? null;
}

function assetName(text: string): string | null {
  return text.match(/\b(Battery|Storage|Generator|Unit|Load|Flexible load) [A-Z0-9]\b/)?.[0] ?? null;
}

function scenarioFamilies(scenario: WorkspaceScenario): ScenarioFamily[] {
  const type = scenario.binding?.type ?? '';
  const families: ScenarioFamily[] = [];
  if (/snsp|inertia/i.test(type)) families.push('system_wide_curtailment');
  else if (type) families.push('local_network_constraint');
  if (/outage/i.test(scenario.summary)) families.push('planned_outage_exposure');
  return families.length ? families : ['cause_unknown'];
}

function illustrativeFact(key: string, value: FactValue, unit: string | null, asOf: string): Fact {
  return { key, value, unit, status: 'supplied', source: 'modelled', sourceName: 'Illustrative fixture (invented)', asOf, history: [] };
}

function window(scenario: WorkspaceScenario): string {
  const time = (iso: string) => iso.slice(11, 16);
  return `${scenario.intervalStart.slice(0, 10)} ${time(scenario.intervalStart)}–${time(scenario.intervalEnd)}`;
}

function situationCase(text: string, createdAt: string, scenarios: WorkspaceScenario[]): OperatorCase {
  const operatorCase = newCase(text, createdAt);
  const match = resolveSituation(text, scenarios);
  if (!match) return { ...operatorCase, scenarios: ['cause_unknown'] };
  const asOf = match.modelRunAt ?? createdAt;
  const waste = match.baseline.dispatchDownWasteMwh;
  const facts: Record<string, Fact> = {
    event_window: illustrativeFact('event_window', window(match), null, asOf),
    affected_area: illustrativeFact('affected_area', match.binding?.location ?? null, null, asOf),
    expected_dispatch_down_mwh: illustrativeFact('expected_dispatch_down_mwh', waste, 'MWh', asOf),
    event_probability: illustrativeFact('event_probability', 70, '%', asOf),
    forecast_range_mwh: illustrativeFact('forecast_range_mwh', waste === null ? null : `${Math.round(waste * 0.6)}–${Math.round(waste * 1.4)}`, 'MWh', asOf),
  };
  return { ...operatorCase, scenarios: scenarioFamilies(match), facts };
}

function caseAction(text: string, family: CaseActionFamily): CaseAction {
  return { family, assetName: assetName(text), facts: {} };
}

export function illustrativeCase(
  description: string,
  comparisonText: string | null,
  createdAt: string,
  scenarios: WorkspaceScenario[],
): OperatorCase {
  const operatorCase = situationCase(description, createdAt, scenarios);
  const family = detectActionFamily(description);
  const proposedAction = family ? caseAction(description, family) : null;
  if (!comparisonText?.trim()) return { ...operatorCase, proposedAction };
  const comparisonFamily = detectActionFamily(comparisonText);
  const comparison = comparisonFamily
    ? { kind: 'action' as const, originalText: comparisonText, action: caseAction(comparisonText, comparisonFamily) }
    : { kind: 'situation' as const, originalText: comparisonText, situation: situationCase(comparisonText, createdAt, scenarios) };
  return { ...operatorCase, proposedAction, comparison };
}

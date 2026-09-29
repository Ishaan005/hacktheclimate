// Operator case record for intake (build issues 04–06 in #32). PROVISIONAL:
// scenario families are a first draft of Issue 01, and the facts per action
// come from the #21 metric tables and acceptance criteria until Issue 03 is
// approved. See docs/INTERACTION_DECISION.md.
//
// One case holds the operator's original words, every fact the tool needs,
// and an optional comparison. A fact is never guessed: when nobody supplied
// or verified it, its status is 'unknown' and its value is null.

import type { ActionFamily, ClarificationAnswer, ClarificationQuestion } from './types';

// Local constraint and system-wide curtailment are EirGrid's own split. An
// unknown cause sends the operator to clarification, never to a guess.
export type ScenarioFamily =
  | 'local_network_constraint'
  | 'system_wide_curtailment'
  | 'planned_outage_exposure'
  | 'cause_unknown';

// Core MVP actions from #21. Voltage and stability support are expanded MVP
// and are left out until their device data exists.
export type CaseActionFamily = ActionFamily;

// Where a value came from. 'forecast' is a model output issued before the
// decision time; 'modelled' is a demo calculation, never a measurement.
export type FactSource = 'operator' | 'measured' | 'forecast' | 'modelled' | 'asset_register' | 'publication';

// supplied: the operator said it. verified: a trusted source confirmed it.
// corrected: the operator overrode an earlier value. stale: the source is
// older than its freshness rule. unknown: nobody supplied it.
export type FactStatus = 'supplied' | 'verified' | 'corrected' | 'stale' | 'unknown';

export type FactValue = number | string | boolean | null;

export type FactKind = 'number' | 'text' | 'choice' | 'time' | 'window';

export type FactDefinition = {
  key: string;
  label: string;
  kind: FactKind;
  unit: string | null;
  // Lower runs first: the question that blocks most of the decision.
  priority: number;
  // Where the value may come from, in order of preference.
  sources: FactSource[];
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  step?: number;
};

export type Fact = {
  key: string;
  value: FactValue;
  unit: string | null;
  status: FactStatus;
  source: FactSource | null;
  // Name of the dataset, model or document, e.g. "GFS national model v3".
  sourceName: string | null;
  // When the value was measured, issued or supplied (UTC ISO).
  asOf: string | null;
  // Earlier values, newest last, so a correction keeps what it replaced.
  history: Omit<Fact, 'history'>[];
};

export type CaseAction = {
  family: CaseActionFamily;
  assetName: string | null;
  facts: Record<string, Fact>;
};

// An alternative action runs on the same case and baseline. A second
// situation needs its own facts and baseline, and the screen labels it as a
// different situation.
export type CaseComparison =
  | { kind: 'action'; originalText: string; action: CaseAction }
  | { kind: 'situation'; originalText: string; situation: OperatorCase };

export type OperatorCase = {
  id: string;
  originalText: string;
  createdAt: string;
  // More than one family may be active at once.
  scenarios: ScenarioFamily[];
  facts: Record<string, Fact>;
  proposedAction: CaseAction | null;
  comparison: CaseComparison | null;
};

const TIME_SOURCES: FactSource[] = ['operator', 'forecast'];
const ASSET_SOURCES: FactSource[] = ['asset_register', 'operator'];

// Facts every case needs before any action can be tested.
export const SITUATION_FACTS: FactDefinition[] = [
  { key: 'event_window', label: 'Event window', kind: 'window', unit: null, priority: 1, sources: TIME_SOURCES },
  { key: 'affected_area', label: 'Affected area or constraint group', kind: 'text', unit: null, priority: 2, sources: ['operator', 'measured'] },
  { key: 'expected_dispatch_down_mwh', label: 'Expected dispatch-down', kind: 'number', unit: 'MWh', priority: 3, sources: ['forecast'], min: 0, max: 5000, step: 1 },
  { key: 'event_probability', label: 'Material-event probability', kind: 'number', unit: '%', priority: 4, sources: ['forecast'], min: 0, max: 100, step: 1 },
  { key: 'forecast_range_mwh', label: 'Forecast range', kind: 'text', unit: 'MWh', priority: 5, sources: ['forecast'] },
];

export const OPTIONAL_SITUATION_FACTS: FactDefinition[] = [
  { key: 'constraint_share_pct', label: 'Constraint share of dispatch-down', kind: 'number', unit: '%', priority: 10, sources: ['forecast', 'measured'], min: 0, max: 100, step: 1 },
  { key: 'peak_half_hour_mw', label: 'Highest expected half-hour average reduction', kind: 'number', unit: 'MW', priority: 11, sources: ['forecast'], min: 0, max: 5000, step: 1 },
  { key: 'existing_instructions', label: 'Instructions already in force', kind: 'text', unit: null, priority: 12, sources: ['operator'] },
];

// Required facts per action, from the #21 acceptance criteria.
export const REQUIRED_ACTION_FACTS: Record<CaseActionFamily, FactDefinition[]> = {
  storage_charging: [
    { key: 'connection_location', label: 'Connection location', kind: 'text', unit: null, priority: 1, sources: ASSET_SOURCES },
    { key: 'max_charging_mw', label: 'Maximum charging power', kind: 'number', unit: 'MW', priority: 2, sources: ASSET_SOURCES, min: 0, max: 1000, step: 1 },
    { key: 'available_mwh', label: 'Available charging energy', kind: 'number', unit: 'MWh', priority: 3, sources: ASSET_SOURCES, min: 0, max: 5000, step: 1 },
    { key: 'state_of_charge_pct', label: 'State of charge at start', kind: 'number', unit: '%', priority: 4, sources: ['measured', 'operator'], min: 0, max: 100, step: 1 },
    { key: 'earliest_start', label: 'Earliest start', kind: 'time', unit: null, priority: 5, sources: ['operator'] },
    { key: 'activation_delay_min', label: 'Activation delay', kind: 'number', unit: 'min', priority: 6, sources: ASSET_SOURCES, min: 0, max: 720, step: 1 },
  ],
  flexible_demand: [
    { key: 'connection_location', label: 'Connection location', kind: 'text', unit: null, priority: 1, sources: ASSET_SOURCES },
    { key: 'available_mw', label: 'Available demand change', kind: 'number', unit: 'MW', priority: 2, sources: ASSET_SOURCES, min: 0, max: 1000, step: 1 },
    {
      key: 'direction', label: 'Direction of demand change', kind: 'choice', unit: null, priority: 3, sources: ['operator', 'modelled'],
      options: [{ value: 'increase', label: 'Increase' }, { value: 'decrease', label: 'Decrease' }],
    },
    { key: 'available_mwh', label: 'Available energy to move', kind: 'number', unit: 'MWh', priority: 4, sources: ASSET_SOURCES, min: 0, max: 5000, step: 1 },
    { key: 'demand_baseline_mw', label: 'Normal demand baseline', kind: 'number', unit: 'MW', priority: 5, sources: ['measured', 'operator'], min: 0, max: 5000, step: 1 },
    { key: 'rebound_mwh', label: 'Rebound energy', kind: 'number', unit: 'MWh', priority: 6, sources: ASSET_SOURCES, min: 0, max: 5000, step: 1 },
    { key: 'earliest_start', label: 'Earliest start', kind: 'time', unit: null, priority: 7, sources: ['operator'] },
    { key: 'activation_delay_min', label: 'Activation delay', kind: 'number', unit: 'min', priority: 8, sources: ASSET_SOURCES, min: 0, max: 720, step: 1 },
    { key: 'max_duration_min', label: 'Maximum duration', kind: 'number', unit: 'min', priority: 9, sources: ASSET_SOURCES, min: 0, max: 1440, step: 1 },
  ],
  generator_redispatch: [
    { key: 'connection_location', label: 'Connection location', kind: 'text', unit: null, priority: 1, sources: ASSET_SOURCES },
    { key: 'scheduled_output_mw', label: 'Scheduled output', kind: 'number', unit: 'MW', priority: 2, sources: ['measured', 'operator'], min: 0, max: 2000, step: 1 },
    { key: 'min_stable_generation_mw', label: 'Minimum stable generation', kind: 'number', unit: 'MW', priority: 3, sources: ASSET_SOURCES, min: 0, max: 2000, step: 1 },
    { key: 'max_output_mw', label: 'Maximum output', kind: 'number', unit: 'MW', priority: 4, sources: ASSET_SOURCES, min: 0, max: 2000, step: 1 },
    { key: 'ramp_rate_mw_per_min', label: 'Ramp rate', kind: 'number', unit: 'MW/min', priority: 5, sources: ASSET_SOURCES, min: 0, max: 200, step: 0.1 },
    { key: 'commitment_restrictions', label: 'Start and stop restrictions', kind: 'text', unit: null, priority: 6, sources: ASSET_SOURCES },
  ],
  outage_review: [
    { key: 'outage_id', label: 'Outage ID', kind: 'text', unit: null, priority: 1, sources: ['publication', 'operator'] },
    { key: 'equipment_description', label: 'Equipment description', kind: 'text', unit: null, priority: 2, sources: ['publication'] },
    { key: 'scheduled_window', label: 'Scheduled start and finish', kind: 'window', unit: null, priority: 3, sources: ['publication'] },
    { key: 'publication_date', label: 'Publication date', kind: 'time', unit: null, priority: 4, sources: ['publication'] },
    { key: 'reviewed_model_asset', label: 'Reviewed model asset', kind: 'text', unit: null, priority: 5, sources: ['publication'] },
    { key: 'alternative_window', label: 'Alternative window to test', kind: 'window', unit: null, priority: 6, sources: ['operator'] },
  ],
};

export const OPTIONAL_ACTION_FACTS: Record<CaseActionFamily, FactDefinition[]> = {
  storage_charging: [
    { key: 'max_duration_min', label: 'Maximum duration', kind: 'number', unit: 'min', priority: 20, sources: ASSET_SOURCES, min: 0, max: 1440, step: 1 },
    { key: 'charging_efficiency_pct', label: 'Charging efficiency', kind: 'number', unit: '%', priority: 21, sources: ASSET_SOURCES, min: 0, max: 100, step: 1 },
    { key: 'charging_cost_eur_per_mwh', label: 'Charging cost', kind: 'number', unit: 'EUR/MWh', priority: 22, sources: ASSET_SOURCES, min: -500, max: 5000, step: 1 },
  ],
  flexible_demand: [
    { key: 'activation_cost_eur', label: 'Activation cost', kind: 'number', unit: 'EUR', priority: 20, sources: ASSET_SOURCES, min: 0, max: 1000000, step: 1 },
  ],
  generator_redispatch: [
    { key: 'operating_cost_eur_per_mwh', label: 'Operating cost', kind: 'number', unit: 'EUR/MWh', priority: 20, sources: ASSET_SOURCES, min: -500, max: 5000, step: 1 },
    { key: 'stability_role', label: 'Required synchronous or stability role', kind: 'text', unit: null, priority: 21, sources: ASSET_SOURCES },
  ],
  outage_review: [
    { key: 'asset_match_confidence', label: 'Asset-match confidence', kind: 'text', unit: null, priority: 20, sources: ['publication'] },
    { key: 'overlapping_outages', label: 'Overlapping outages', kind: 'text', unit: null, priority: 21, sources: ['publication', 'operator'] },
  ],
};

export function unknownFact(definition: FactDefinition): Fact {
  return { key: definition.key, value: null, unit: definition.unit, status: 'unknown', source: null, sourceName: null, asOf: null, history: [] };
}

// A stale value is not trusted for a decision, so it counts as missing.
export function isMissing(fact: Fact | undefined): boolean {
  return !fact || fact.value === null || fact.status === 'unknown' || fact.status === 'stale';
}

// The operator overrides a fact. The earlier value moves to history.
export function correctFact(fact: Fact, value: FactValue, asOf: string): Fact {
  const { history, ...previous } = fact;
  return { ...fact, value, status: 'corrected', source: 'operator', sourceName: 'Operator correction', asOf, history: [...history, previous] };
}

export const SCENARIO_DEFINITION: FactDefinition = {
  key: 'scenario',
  label: 'What is limiting renewable output?',
  kind: 'choice',
  unit: null,
  priority: 0,
  sources: ['operator'],
  options: [
    { value: 'local_network_constraint', label: 'Local network limit (line, transformer or area)' },
    { value: 'system_wide_curtailment', label: 'System-wide limit (SNSP, inertia or minimum units)' },
    { value: 'planned_outage_exposure', label: 'A planned outage makes the limit worse' },
  ],
};

export type MissingFact = {
  // 'situation', 'proposed', or 'comparison' so a question can say which
  // action or situation it is about.
  scope: 'situation' | 'proposed' | 'comparison';
  definition: FactDefinition;
};

function missingIn(facts: Record<string, Fact>, definitions: FactDefinition[], scope: MissingFact['scope']): MissingFact[] {
  return definitions.filter((definition) => isMissing(facts[definition.key])).map((definition) => ({ scope, definition }));
}

// Required facts still missing, most blocking first. Situation facts come
// before action facts: no action can be tested without the situation. An
// unknown cause blocks everything, so it is always asked first.
export function missingRequiredFacts(operatorCase: OperatorCase): MissingFact[] {
  const missing: MissingFact[] = [];
  if (!operatorCase.scenarios.length || operatorCase.scenarios.includes('cause_unknown')) {
    missing.push({ scope: 'situation', definition: SCENARIO_DEFINITION });
  }
  missing.push(...missingIn(operatorCase.facts, SITUATION_FACTS, 'situation'));
  if (operatorCase.proposedAction) {
    const { family, facts } = operatorCase.proposedAction;
    missing.push(...missingIn(facts, REQUIRED_ACTION_FACTS[family], 'proposed'));
  }
  const comparison = operatorCase.comparison;
  if (comparison?.kind === 'action') {
    missing.push(...missingIn(comparison.action.facts, REQUIRED_ACTION_FACTS[comparison.action.family], 'comparison'));
  } else if (comparison?.kind === 'situation') {
    missing.push(...missingRequiredFacts(comparison.situation).map((item) => ({ ...item, scope: 'comparison' as const })));
  }
  const scopeOrder = { situation: 0, proposed: 1, comparison: 2 };
  return missing.sort((a, b) => scopeOrder[a.scope] - scopeOrder[b.scope] || a.definition.priority - b.definition.priority);
}

// A case can go to evaluation only when no required fact is missing.
export function readyForEvaluation(operatorCase: OperatorCase): boolean {
  return missingRequiredFacts(operatorCase).length === 0;
}

const SCOPE_PREFIX: Record<MissingFact['scope'], string> = {
  situation: '',
  proposed: 'Your action: ',
  comparison: 'Comparison: ',
};

// Turns missing facts into questions for ClarificationForm. Question IDs
// carry the scope so a proposed and a comparison action can both ask for,
// say, connection_location in the same round.
export function clarificationQuestions(missing: MissingFact[]): ClarificationQuestion[] {
  return missing.map(({ scope, definition }) => {
    const base = {
      id: `${scope}.${definition.key}`,
      prompt: `${SCOPE_PREFIX[scope]}${definition.label}`,
      helpText: definition.unit ? `Unit: ${definition.unit}` : null,
      required: true,
    };
    if (definition.kind === 'choice' && definition.options) {
      return { ...base, kind: 'single_choice', options: definition.options };
    }
    if (definition.kind === 'number' && definition.min !== undefined && definition.max !== undefined && definition.step !== undefined) {
      return { ...base, kind: 'number', min: definition.min, max: definition.max, step: definition.step, unit: definition.unit, defaultValue: null };
    }
    const placeholder = definition.kind === 'window' ? 'e.g. 14:00–17:00' : definition.kind === 'time' ? 'e.g. 14:30' : null;
    return { ...base, kind: 'text', placeholder, maxLength: 200 };
  });
}

export function newCase(originalText: string, createdAt: string): OperatorCase {
  return { id: `case-${createdAt}`, originalText, createdAt, scenarios: [], facts: {}, proposedAction: null, comparison: null };
}

// Records one operator value. A new value on a known fact is a correction and
// keeps the old value in history; the same value again changes nothing.
function recordFact(facts: Record<string, Fact>, key: string, value: FactValue, unit: string | null, asOf: string): Record<string, Fact> {
  const existing = facts[key];
  if (existing && !isMissing(existing)) {
    return existing.value === value ? facts : { ...facts, [key]: correctFact(existing, value, asOf) };
  }
  const supplied: Fact = {
    key, value, unit, status: 'supplied', source: 'operator', sourceName: 'Operator answer', asOf, history: existing?.history ?? [],
  };
  return { ...facts, [key]: supplied };
}

const SCENARIO_FAMILIES: ScenarioFamily[] = ['local_network_constraint', 'system_wide_curtailment', 'planned_outage_exposure', 'cause_unknown'];

function recordSituationFact(situation: OperatorCase, key: string, value: FactValue, unit: string | null, asOf: string): OperatorCase {
  if (key === SCENARIO_DEFINITION.key && SCENARIO_FAMILIES.includes(value as ScenarioFamily)) {
    return { ...situation, scenarios: [value as ScenarioFamily] };
  }
  const facts = recordFact(situation.facts, key, value, unit, asOf);
  return facts === situation.facts ? situation : { ...situation, facts };
}

// Saves an operator answer or correction into the case. `id` is either a
// scoped id from clarificationQuestions ("proposed.max_charging_mw") or a
// solver question id, which is kept as a situation fact under that id. A
// scope with nothing to attach to (no proposed action yet) also falls back to
// a situation fact, so no answer is lost.
export function setCaseFact(operatorCase: OperatorCase, id: string, value: FactValue, unit: string | null, asOf: string): OperatorCase {
  const dot = id.indexOf('.');
  const scope = dot > 0 ? id.slice(0, dot) : null;
  const key = dot > 0 ? id.slice(dot + 1) : id;
  const { proposedAction, comparison } = operatorCase;
  if (scope === 'situation') return recordSituationFact(operatorCase, key, value, unit, asOf);
  if (scope === 'proposed' && proposedAction) {
    return { ...operatorCase, proposedAction: { ...proposedAction, facts: recordFact(proposedAction.facts, key, value, unit, asOf) } };
  }
  if (scope === 'comparison' && comparison?.kind === 'action') {
    const action = { ...comparison.action, facts: recordFact(comparison.action.facts, key, value, unit, asOf) };
    return { ...operatorCase, comparison: { ...comparison, action } };
  }
  if (scope === 'comparison' && comparison?.kind === 'situation') {
    return { ...operatorCase, comparison: { ...comparison, situation: recordSituationFact(comparison.situation, key, value, unit, asOf) } };
  }
  return recordSituationFact(operatorCase, id, value, unit, asOf);
}

// Saves one round of clarification answers. Skipped optional questions stay
// unknown; a multi-choice answer is stored as a comma-separated list.
export function applyAnswers(
  operatorCase: OperatorCase,
  questions: ClarificationQuestion[],
  answers: ClarificationAnswer[],
  asOf: string,
): OperatorCase {
  return answers.reduce((current, answer) => {
    if (answer.value === null) return current;
    const question = questions.find((item) => item.id === answer.questionId);
    const unit = question?.kind === 'number' ? question.unit : null;
    const value = Array.isArray(answer.value) ? answer.value.join(', ') : answer.value;
    return setCaseFact(current, answer.questionId, value, unit, asOf);
  }, operatorCase);
}

export const SCENARIO_LABEL: Record<ScenarioFamily, string> = {
  local_network_constraint: 'Local network limit',
  system_wide_curtailment: 'System-wide limit',
  planned_outage_exposure: 'Planned outage makes it worse',
  cause_unknown: 'Cause unknown',
};

// One row of the fact review table. `id` is the scoped id setCaseFact takes.
export type ReviewRow = {
  id: string;
  definition: FactDefinition;
  fact: Fact | null;
  required: boolean;
};

export type ReviewSection = {
  scope: MissingFact['scope'];
  title: string;
  rows: ReviewRow[];
};

function rowsFor(
  scope: MissingFact['scope'],
  facts: Record<string, Fact>,
  required: FactDefinition[],
  optional: FactDefinition[],
): ReviewRow[] {
  const known = new Set([...required, ...optional].map((definition) => definition.key));
  const rows: ReviewRow[] = [
    ...required.map((definition) => ({ id: `${scope}.${definition.key}`, definition, fact: facts[definition.key] ?? null, required: true })),
    // Optional facts only take space once someone has supplied them.
    ...optional
      .filter((definition) => facts[definition.key])
      .map((definition) => ({ id: `${scope}.${definition.key}`, definition, fact: facts[definition.key], required: false })),
  ];
  // Answers to solver questions have no definition; show them as plain text.
  for (const fact of Object.values(facts)) {
    if (known.has(fact.key)) continue;
    const definition: FactDefinition = { key: fact.key, label: fact.key.replace(/[._]/g, ' '), kind: 'text', unit: fact.unit, priority: 99, sources: ['operator'] };
    rows.push({ id: `${scope}.${fact.key}`, definition, fact, required: false });
  }
  return rows;
}

function situationRows(scope: MissingFact['scope'], situation: OperatorCase): ReviewRow[] {
  const scenarioKnown = situation.scenarios.length > 0 && !situation.scenarios.includes('cause_unknown');
  const scenarioFact: Fact | null = scenarioKnown
    ? {
      key: SCENARIO_DEFINITION.key,
      value: situation.scenarios.map((family) => SCENARIO_LABEL[family]).join(', '),
      unit: null, status: 'supplied', source: 'operator', sourceName: 'Operator description', asOf: situation.createdAt, history: [],
    }
    : null;
  return [
    { id: `${scope}.${SCENARIO_DEFINITION.key}`, definition: SCENARIO_DEFINITION, fact: scenarioFact, required: true },
    ...rowsFor(scope, situation.facts, SITUATION_FACTS, OPTIONAL_SITUATION_FACTS),
  ];
}

function actionTitle(prefix: string, action: CaseAction): string {
  const family = ACTION_TITLE[action.family];
  return action.assetName ? `${prefix}: ${family}, ${action.assetName}` : `${prefix}: ${family}`;
}

const ACTION_TITLE: Record<CaseActionFamily, string> = {
  storage_charging: 'storage charging',
  flexible_demand: 'flexible demand',
  generator_redispatch: 'generator redispatch',
  outage_review: 'planned-outage review',
};

// Everything the review table shows, grouped the same way the questions are
// ordered: the situation, the operator's action, then the comparison.
export function reviewSections(operatorCase: OperatorCase): ReviewSection[] {
  const sections: ReviewSection[] = [{ scope: 'situation', title: 'Situation', rows: situationRows('situation', operatorCase) }];
  const { proposedAction, comparison } = operatorCase;
  if (proposedAction) {
    sections.push({
      scope: 'proposed',
      title: actionTitle('Your action', proposedAction),
      rows: rowsFor('proposed', proposedAction.facts, REQUIRED_ACTION_FACTS[proposedAction.family], OPTIONAL_ACTION_FACTS[proposedAction.family]),
    });
  }
  if (comparison?.kind === 'action') {
    const { action } = comparison;
    sections.push({
      scope: 'comparison',
      title: actionTitle('Comparison', action),
      rows: rowsFor('comparison', action.facts, REQUIRED_ACTION_FACTS[action.family], OPTIONAL_ACTION_FACTS[action.family]),
    });
  } else if (comparison?.kind === 'situation') {
    sections.push({ scope: 'comparison', title: 'Comparison: a different situation', rows: situationRows('comparison', comparison.situation) });
  }
  return sections;
}

function factLines(rows: ReviewRow[]): string[] {
  return rows
    .filter((row) => row.fact && !isMissing(row.fact))
    .map((row) => {
      const fact = row.fact as Fact;
      const unit = fact.unit ? ` ${fact.unit}` : '';
      return `- ${row.definition.label}: ${fact.value}${unit} (${fact.sourceName ?? fact.source ?? 'unknown source'})`;
    });
}

// The reviewed case as text for the solver: the operator's words, then every
// confirmed fact with its source, so the solver works from checked facts.
export function caseSummaryText(operatorCase: OperatorCase): string {
  const lines = [operatorCase.originalText, '', 'Reviewed facts:'];
  for (const section of reviewSections(operatorCase)) {
    const facts = factLines(section.rows);
    if (!facts.length) continue;
    lines.push(`${section.title}:`, ...facts);
  }
  if (operatorCase.comparison) lines.push('', `Operator comparison request: ${operatorCase.comparison.originalText}`);
  return lines.join('\n');
}

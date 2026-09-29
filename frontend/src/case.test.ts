import { describe, expect, it } from 'vitest';
import {
  applyAnswers,
  clarificationQuestions,
  correctFact,
  missingRequiredFacts,
  newCase,
  readyForEvaluation,
  REQUIRED_ACTION_FACTS,
  setCaseFact,
  SITUATION_FACTS,
  unknownFact,
} from './case';
import { parseClarificationRequest } from './clarification';
import type { CaseAction, Fact, FactDefinition, OperatorCase } from './case';

function known(definition: FactDefinition, value: Fact['value'] = 1): Fact {
  return { ...unknownFact(definition), value, status: 'verified', source: 'forecast', sourceName: 'test', asOf: '2026-09-29T06:00Z' };
}

function allKnown(definitions: FactDefinition[]): Record<string, Fact> {
  return Object.fromEntries(definitions.map((definition) => [definition.key, known(definition)]));
}

function baseCase(overrides: Partial<OperatorCase> = {}): OperatorCase {
  return {
    id: 'case-1',
    originalText: 'NW constraint 14:00–17:00',
    createdAt: '2026-09-29T08:00Z',
    scenarios: ['local_network_constraint'],
    facts: allKnown(SITUATION_FACTS),
    proposedAction: null,
    comparison: null,
    ...overrides,
  };
}

function storage(facts: Record<string, Fact> = {}): CaseAction {
  return { family: 'storage_charging', assetName: 'Battery A', facts };
}

describe('missingRequiredFacts', () => {
  it('is empty when every required situation fact is known', () => {
    expect(missingRequiredFacts(baseCase())).toEqual([]);
    expect(readyForEvaluation(baseCase())).toBe(true);
  });

  it('asks for the scenario first when the cause is unknown', () => {
    const missing = missingRequiredFacts(baseCase({ scenarios: ['cause_unknown'], facts: {} }));
    expect(missing[0].definition.key).toBe('scenario');
    expect(missing[1].definition.key).toBe('event_window');
  });

  it('treats a stale fact as missing', () => {
    const facts = allKnown(SITUATION_FACTS);
    facts.event_window = { ...facts.event_window, status: 'stale' };
    expect(missingRequiredFacts(baseCase({ facts })).map((item) => item.definition.key)).toEqual(['event_window']);
  });

  it('orders situation facts before proposed-action facts before comparison facts', () => {
    const facts = allKnown(SITUATION_FACTS);
    delete facts.affected_area;
    const missing = missingRequiredFacts(baseCase({
      facts,
      proposedAction: storage(),
      comparison: { kind: 'action', originalText: 'Reduce Generator B', action: { family: 'generator_redispatch', assetName: 'Generator B', facts: {} } },
    }));
    expect(missing[0]).toMatchObject({ scope: 'situation', definition: { key: 'affected_area' } });
    const scopes = missing.map((item) => item.scope);
    expect(scopes.lastIndexOf('proposed')).toBeLessThan(scopes.indexOf('comparison'));
    expect(missing.filter((item) => item.scope === 'proposed')).toHaveLength(REQUIRED_ACTION_FACTS.storage_charging.length);
  });

  it('checks a second situation against its own facts', () => {
    const missing = missingRequiredFacts(baseCase({
      comparison: { kind: 'situation', originalText: 'Same but tomorrow', situation: baseCase({ id: 'case-2', facts: {} }) },
    }));
    expect(missing).toHaveLength(SITUATION_FACTS.length);
    expect(missing.every((item) => item.scope === 'comparison')).toBe(true);
  });
});

describe('correctFact', () => {
  it('keeps the replaced value in history', () => {
    const original = known(SITUATION_FACTS[0], '14:00–17:00');
    const corrected = correctFact(original, '14:00–18:00', '2026-09-29T08:05Z');
    expect(corrected).toMatchObject({ value: '14:00–18:00', status: 'corrected', source: 'operator' });
    const { history: _history, ...previous } = original;
    expect(corrected.history).toEqual([previous]);
  });
});

describe('clarificationQuestions', () => {
  it('builds questions the clarification parser accepts, with scoped ids', () => {
    const missing = missingRequiredFacts(baseCase({ scenarios: ['cause_unknown'], facts: {}, proposedAction: storage() }));
    const questions = clarificationQuestions(missing);
    expect(() => parseClarificationRequest({ reason: 'Missing facts', questions })).not.toThrow();
    expect(questions[0]).toMatchObject({ id: 'situation.scenario', kind: 'single_choice' });
    expect(questions.find((question) => question.id === 'proposed.max_charging_mw')).toMatchObject({ kind: 'number', unit: 'MW', prompt: 'Your action: Maximum charging power' });
  });
});

describe('applyAnswers and setCaseFact', () => {
  const asOf = '2026-09-29T08:10Z';

  it('saves scoped answers to the situation, proposed action and comparison action', () => {
    const start = baseCase({
      scenarios: ['cause_unknown'],
      facts: {},
      proposedAction: storage(),
      comparison: { kind: 'action', originalText: 'Reduce Generator B', action: { family: 'generator_redispatch', assetName: 'Generator B', facts: {} } },
    });
    const questions = clarificationQuestions(missingRequiredFacts(start));
    const next = applyAnswers(start, questions, [
      { round: 1, questionId: 'situation.scenario', value: 'local_network_constraint' },
      { round: 1, questionId: 'situation.event_window', value: '14:00–17:00' },
      { round: 1, questionId: 'proposed.max_charging_mw', value: 40 },
      { round: 1, questionId: 'comparison.max_output_mw', value: 400 },
      { round: 1, questionId: 'situation.affected_area', value: null },
    ], asOf);
    expect(next.scenarios).toEqual(['local_network_constraint']);
    expect(next.facts.event_window).toMatchObject({ value: '14:00–17:00', status: 'supplied', source: 'operator', asOf });
    expect(next.facts.affected_area).toBeUndefined();
    expect(next.proposedAction?.facts.max_charging_mw).toMatchObject({ value: 40, unit: 'MW' });
    expect(next.comparison?.kind === 'action' && next.comparison.action.facts.max_output_mw.value).toBe(400);
    expect(start.facts).toEqual({});
  });

  it('saves a second situation\'s answers to that situation', () => {
    const start = baseCase({ comparison: { kind: 'situation', originalText: 'Tomorrow', situation: baseCase({ id: 'case-2', facts: {} }) } });
    const next = setCaseFact(start, 'comparison.event_window', '09:00–11:00', null, asOf);
    expect(next.comparison?.kind === 'situation' && next.comparison.situation.facts.event_window.value).toBe('09:00–11:00');
    expect(next.facts.event_window).toEqual(start.facts.event_window);
  });

  it('keeps unscoped solver answers as situation facts and joins multi-choice values', () => {
    const next = applyAnswers(newCase('problem', asOf), [], [{ round: 1, questionId: 'area', value: ['west', 'north_west'] }], asOf);
    expect(next.facts.area.value).toBe('west, north_west');
  });

  it('treats a new value on a known fact as a correction, and the same value as no change', () => {
    const start = baseCase();
    const corrected = setCaseFact(start, 'situation.event_window', '14:00–18:00', null, asOf);
    expect(corrected.facts.event_window).toMatchObject({ value: '14:00–18:00', status: 'corrected' });
    expect(corrected.facts.event_window.history).toHaveLength(1);
    expect(setCaseFact(corrected, 'situation.event_window', '14:00–18:00', null, asOf)).toBe(corrected);
  });

  it('keeps a proposed-action answer as a situation fact when there is no proposed action', () => {
    const next = setCaseFact(newCase('x', asOf), 'proposed.max_charging_mw', 40, 'MW', asOf);
    expect(next.facts['proposed.max_charging_mw'].value).toBe(40);
  });
});

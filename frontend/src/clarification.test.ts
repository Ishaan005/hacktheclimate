import { describe, expect, it } from 'vitest';
import { answerLabel, InvalidClarificationError, parseClarificationRequest, toAnswers, validateAnswer } from './clarification';
import { illustrativeClarification } from './fixtures/illustrativeClarification';
import type { MultiChoiceQuestion, NumberQuestion, SingleChoiceQuestion, TextQuestion } from './types';

const [limit, area, leadTime, detail] = illustrativeClarification.questions as [
  SingleChoiceQuestion,
  MultiChoiceQuestion,
  NumberQuestion,
  TextQuestion,
];

function withQuestion(question: Record<string, unknown>) {
  return { reason: 'Need more detail.', questions: [question] };
}

describe('parseClarificationRequest', () => {
  it('accepts the illustrative request unchanged', () => {
    expect(parseClarificationRequest(illustrativeClarification)).toEqual(illustrativeClarification);
  });

  it('fills optional fields with null', () => {
    const parsed = parseClarificationRequest(withQuestion({ id: 'q', kind: 'number', prompt: 'MW?', min: 0, max: 10, step: 1 }));
    expect(parsed.questions[0]).toEqual({
      id: 'q', kind: 'number', prompt: 'MW?', helpText: null, required: false,
      min: 0, max: 10, step: 1, unit: null, defaultValue: null,
    });
  });

  it.each([
    ['a non-object', null],
    ['no questions', { reason: 'x', questions: [] }],
    ['a missing reason', { questions: [{ id: 'q', kind: 'text', prompt: 'p' }] }],
    ['an unknown kind', withQuestion({ id: 'q', kind: 'date', prompt: 'p' })],
    ['one option', withQuestion({ id: 'q', kind: 'single_choice', prompt: 'p', options: [{ value: 'a', label: 'A' }] })],
    ['duplicate option values', withQuestion({
      id: 'q', kind: 'single_choice', prompt: 'p', options: [{ value: 'a', label: 'A' }, { value: 'a', label: 'B' }],
    })],
    ['min above max selected', withQuestion({
      id: 'q', kind: 'multi_choice', prompt: 'p', minSelected: 2, maxSelected: 1,
      options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }],
    })],
    ['min not below max', withQuestion({ id: 'q', kind: 'number', prompt: 'p', min: 5, max: 5, step: 1 })],
    ['a zero step', withQuestion({ id: 'q', kind: 'number', prompt: 'p', min: 0, max: 5, step: 0 })],
    ['a default outside the range', withQuestion({ id: 'q', kind: 'number', prompt: 'p', min: 0, max: 5, step: 1, defaultValue: 9 })],
    ['duplicate question ids', { reason: 'x', questions: [
      { id: 'q', kind: 'text', prompt: 'p' },
      { id: 'q', kind: 'text', prompt: 'p' },
    ] }],
  ])('rejects %s', (_label, raw) => {
    expect(() => parseClarificationRequest(raw)).toThrow(InvalidClarificationError);
  });
});

describe('validateAnswer', () => {
  it('requires required answers and allows blank optional ones', () => {
    expect(validateAnswer(limit, null)).toMatch(/Answer this question/);
    expect(validateAnswer(area, [])).toMatch(/Answer this question/);
    expect(validateAnswer(leadTime, null)).toBeNull();
    expect(validateAnswer(detail, '')).toBeNull();
  });

  it('checks choices, counts, ranges and length', () => {
    expect(validateAnswer(limit, 'thermal')).toBeNull();
    expect(validateAnswer(limit, 'made_up')).toBe('Choose one option.');
    expect(validateAnswer(area, ['west', 'south', 'dublin', 'south_east'])).toBe('Choose no more than 3.');
    expect(validateAnswer(leadTime, 300)).toBe('Enter a value from 0 to 240 min.');
    expect(validateAnswer(leadTime, 60)).toBeNull();
    expect(validateAnswer(detail, 'x'.repeat(301))).toBe('Use 300 characters or fewer.');
  });
});

describe('answers', () => {
  it('sends blank optional answers as null', () => {
    const answers = toAnswers(illustrativeClarification.questions, { limit: 'thermal', area: ['west'], lead_time: null, detail: '' }, 1);
    expect(answers).toEqual([
      { round: 1, questionId: 'limit', value: 'thermal' },
      { round: 1, questionId: 'area', value: ['west'] },
      { round: 1, questionId: 'lead_time', value: null },
      { round: 1, questionId: 'detail', value: null },
    ]);
  });

  it('labels answers in plain language', () => {
    expect(answerLabel(area, ['west', 'dublin'])).toBe('West, Dublin');
    expect(answerLabel(leadTime, 45)).toBe('45 min');
    expect(answerLabel(detail, null)).toBeNull();
  });
});

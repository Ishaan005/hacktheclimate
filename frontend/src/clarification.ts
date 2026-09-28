// Follow-up questions from the situation solver. The LLM output lands in
// parseClarificationRequest first: nothing reaches the form until its shape
// is checked, because a malformed question must fail loudly, not render as
// an empty control.

import type {
  ChoiceOption,
  ClarificationAnswer,
  ClarificationAnswerValue,
  ClarificationQuestion,
  ClarificationRequest,
} from './types';

export class InvalidClarificationError extends Error {}

type Raw = Record<string, unknown>;

function isRecord(value: unknown): value is Raw {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(raw: Raw, key: string, where: string): string {
  const value = raw[key];
  if (typeof value !== 'string' || !value.trim()) {
    throw new InvalidClarificationError(`${where}: "${key}" must be a non-empty string`);
  }
  return value;
}

function optionalText(raw: Raw, key: string): string | null {
  return typeof raw[key] === 'string' && (raw[key] as string).trim() ? (raw[key] as string) : null;
}

function finite(raw: Raw, key: string, where: string): number {
  const value = raw[key];
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new InvalidClarificationError(`${where}: "${key}" must be a number`);
  }
  return value;
}

function optionalCount(raw: Raw, key: string, where: string): number | null {
  if (raw[key] === undefined || raw[key] === null) return null;
  const value = finite(raw, key, where);
  if (!Number.isInteger(value) || value < 0) {
    throw new InvalidClarificationError(`${where}: "${key}" must be a whole number`);
  }
  return value;
}

function options(raw: Raw, where: string): ChoiceOption[] {
  const list = raw.options;
  if (!Array.isArray(list) || list.length < 2) {
    throw new InvalidClarificationError(`${where}: needs at least two options`);
  }
  const parsed = list.map((option, index) => {
    if (!isRecord(option)) throw new InvalidClarificationError(`${where}: option ${index} is not an object`);
    return { value: text(option, 'value', where), label: text(option, 'label', where) };
  });
  if (new Set(parsed.map((option) => option.value)).size !== parsed.length) {
    throw new InvalidClarificationError(`${where}: option values must be unique`);
  }
  return parsed;
}

function parseQuestion(raw: unknown, index: number): ClarificationQuestion {
  const where = `question ${index}`;
  if (!isRecord(raw)) throw new InvalidClarificationError(`${where}: not an object`);
  const base = {
    id: text(raw, 'id', where),
    prompt: text(raw, 'prompt', where),
    helpText: optionalText(raw, 'helpText'),
    required: raw.required === true,
  };
  switch (raw.kind) {
    case 'text':
      return { ...base, kind: 'text', placeholder: optionalText(raw, 'placeholder'), maxLength: optionalCount(raw, 'maxLength', where) };
    case 'single_choice':
      return { ...base, kind: 'single_choice', options: options(raw, where) };
    case 'multi_choice': {
      const parsed = options(raw, where);
      const minSelected = optionalCount(raw, 'minSelected', where);
      const maxSelected = optionalCount(raw, 'maxSelected', where);
      if (minSelected !== null && maxSelected !== null && minSelected > maxSelected) {
        throw new InvalidClarificationError(`${where}: minSelected is above maxSelected`);
      }
      if (minSelected !== null && minSelected > parsed.length) {
        throw new InvalidClarificationError(`${where}: minSelected is above the number of options`);
      }
      return { ...base, kind: 'multi_choice', options: parsed, minSelected, maxSelected };
    }
    case 'number': {
      const min = finite(raw, 'min', where);
      const max = finite(raw, 'max', where);
      const step = finite(raw, 'step', where);
      if (min >= max) throw new InvalidClarificationError(`${where}: min must be below max`);
      if (step <= 0) throw new InvalidClarificationError(`${where}: step must be positive`);
      const defaultValue = raw.defaultValue === undefined || raw.defaultValue === null ? null : finite(raw, 'defaultValue', where);
      if (defaultValue !== null && (defaultValue < min || defaultValue > max)) {
        throw new InvalidClarificationError(`${where}: defaultValue is outside min and max`);
      }
      return { ...base, kind: 'number', min, max, step, unit: optionalText(raw, 'unit'), defaultValue };
    }
    default:
      throw new InvalidClarificationError(`${where}: unknown kind ${JSON.stringify(raw.kind)}`);
  }
}

export function parseClarificationRequest(raw: unknown): ClarificationRequest {
  if (!isRecord(raw)) throw new InvalidClarificationError('clarification: not an object');
  const reason = text(raw, 'reason', 'clarification');
  if (!Array.isArray(raw.questions) || raw.questions.length === 0) {
    throw new InvalidClarificationError('clarification: needs at least one question');
  }
  const questions = raw.questions.map(parseQuestion);
  if (new Set(questions.map((question) => question.id)).size !== questions.length) {
    throw new InvalidClarificationError('clarification: question ids must be unique');
  }
  return { reason, questions };
}

// Starting value for each control. A number question without a default stays
// unset: the slider position alone is not an answer.
export function initialAnswer(question: ClarificationQuestion): ClarificationAnswerValue {
  switch (question.kind) {
    case 'text':
      return '';
    case 'single_choice':
      return null;
    case 'multi_choice':
      return [];
    case 'number':
      return question.defaultValue;
  }
}

export function isEmptyAnswer(value: ClarificationAnswerValue): boolean {
  return value === null || value === '' || (Array.isArray(value) && value.length === 0);
}

// Returns a message to show beside the control, or null when the answer is
// acceptable.
export function validateAnswer(question: ClarificationQuestion, value: ClarificationAnswerValue): string | null {
  if (isEmptyAnswer(value)) return question.required ? 'Answer this question to continue.' : null;
  switch (question.kind) {
    case 'text':
      if (typeof value !== 'string') return 'Enter text.';
      if (question.maxLength !== null && value.length > question.maxLength) {
        return `Use ${question.maxLength} characters or fewer.`;
      }
      return null;
    case 'single_choice':
      return question.options.some((option) => option.value === value) ? null : 'Choose one option.';
    case 'multi_choice': {
      if (!Array.isArray(value)) return 'Choose from the options.';
      if (question.minSelected !== null && value.length < question.minSelected) {
        return `Choose at least ${question.minSelected}.`;
      }
      if (question.maxSelected !== null && value.length > question.maxSelected) {
        return `Choose no more than ${question.maxSelected}.`;
      }
      return null;
    }
    case 'number': {
      if (typeof value !== 'number' || !Number.isFinite(value)) return 'Enter a number.';
      const unit = question.unit ? ` ${question.unit}` : '';
      if (value < question.min || value > question.max) {
        return `Enter a value from ${question.min} to ${question.max}${unit}.`;
      }
      return null;
    }
  }
}

// Empty optional answers go back as null so the solver can tell "left blank"
// from an actual value.
export function toAnswers(questions: ClarificationQuestion[], values: Record<string, ClarificationAnswerValue>): ClarificationAnswer[] {
  return questions.map((question) => {
    const value = values[question.id] ?? null;
    return { questionId: question.id, value: isEmptyAnswer(value) ? null : value };
  });
}

// Plain-language answer text, e.g. for the offline matcher or a summary line.
export function answerLabel(question: ClarificationQuestion, value: ClarificationAnswerValue): string | null {
  if (isEmptyAnswer(value)) return null;
  switch (question.kind) {
    case 'single_choice':
    case 'multi_choice': {
      const selected = Array.isArray(value) ? value : [value];
      return question.options.filter((option) => selected.includes(option.value)).map((option) => option.label).join(', ');
    }
    case 'number':
      return question.unit ? `${value} ${question.unit}` : String(value);
    case 'text':
      return String(value);
  }
}

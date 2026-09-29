// Keeps the operator's case in localStorage so a reload resumes it (build
// issue 06). Anything that does not match the saved shape is dropped rather
// than half-restored: a partly restored case could show a question as
// answered when it was not.

import { parseClarificationRequest } from './clarification';
import type { OperatorCase } from './case';
import type { Extraction } from './api';
import type { ClarificationRequest, SolverRequest, SolverResult } from './types';

export const STORAGE_KEY = 'eirgrid-mvp.case.v1';

// Only settled states are saved. A request in flight is saved as the request
// itself and runs again on reload.
export type SavedState =
  | { status: 'reviewing'; extraction: Extraction }
  | { status: 'clarifying'; clarification: ClarificationRequest; round: number }
  | { status: 'stopped'; missing: string[]; round: number }
  | { status: 'solved'; result: Exclude<SolverResult, { kind: 'clarification' }> }
  | { status: 'pending' };

export type SavedSession = {
  version: 1;
  request: SolverRequest;
  round: number;
  operatorCase: OperatorCase;
  state: SavedState;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isRequest(value: unknown): value is SolverRequest {
  return isRecord(value) && typeof value.description === 'string' && Array.isArray(value.answers)
    && (value.threadId === null || typeof value.threadId === 'string')
    && (value.caseSummary === undefined || typeof value.caseSummary === 'string');
}

export function isCase(value: unknown): value is OperatorCase {
  return isRecord(value) && typeof value.id === 'string' && typeof value.originalText === 'string'
    && Array.isArray(value.scenarios) && isRecord(value.facts);
}

const EXTRACTIONS = new Set(['llm', 'rules', 'fixture', 'manual']);

const SOLVED_KINDS = new Set(['scenario', 'dispatch_down_risk', 'assistant_reply']);

function parseState(raw: unknown): SavedState {
  if (!isRecord(raw)) throw new Error('state is not an object');
  switch (raw.status) {
    case 'reviewing':
      if (!EXTRACTIONS.has(raw.extraction as string)) throw new Error('reviewing state malformed');
      return { status: 'reviewing', extraction: raw.extraction as Extraction };
    case 'clarifying':
      if (typeof raw.round !== 'number') throw new Error('round missing');
      return { status: 'clarifying', clarification: parseClarificationRequest(raw.clarification), round: raw.round };
    case 'stopped':
      if (typeof raw.round !== 'number' || !Array.isArray(raw.missing) || !raw.missing.every((item) => typeof item === 'string')) {
        throw new Error('stopped state malformed');
      }
      return { status: 'stopped', missing: raw.missing, round: raw.round };
    case 'solved':
      if (!isRecord(raw.result) || !SOLVED_KINDS.has(raw.result.kind as string)) throw new Error('result malformed');
      return { status: 'solved', result: raw.result as Exclude<SolverResult, { kind: 'clarification' }> };
    case 'pending':
      return { status: 'pending' };
    default:
      throw new Error(`unknown status ${JSON.stringify(raw.status)}`);
  }
}

export function loadSession(): SavedSession | null {
  let text: string | null;
  try {
    text = localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
  if (!text) return null;
  try {
    const raw: unknown = JSON.parse(text);
    if (!isRecord(raw) || raw.version !== 1 || typeof raw.round !== 'number' || !isRequest(raw.request) || !isCase(raw.operatorCase)) {
      throw new Error('session malformed');
    }
    return { version: 1, request: raw.request, round: raw.round, operatorCase: raw.operatorCase, state: parseState(raw.state) };
  } catch (error) {
    console.error('Discarding saved case:', error);
    clearSession();
    return null;
  }
}

// Storage can be full or blocked (private browsing). The case still works
// for this page; it just will not survive a reload.
export function saveSession(session: SavedSession) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch (error) {
    console.error('Could not save case:', error);
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing saved to clear.
  }
}

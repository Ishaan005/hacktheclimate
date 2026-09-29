import { afterEach, describe, expect, it, vi } from 'vitest';
import { newCase } from './case';
import { clearSession, loadSession, saveSession, STORAGE_KEY } from './caseStore';
import { illustrativeClarification } from './fixtures/illustrativeClarification';
import type { SavedSession } from './caseStore';

const session: SavedSession = {
  version: 1,
  request: { description: 'problem', threadId: 'thread-1', answers: [] },
  round: 1,
  operatorCase: newCase('problem', '2026-09-29T08:00Z'),
  state: { status: 'clarifying', clarification: illustrativeClarification, round: 1 },
};

afterEach(() => vi.restoreAllMocks());

describe('caseStore', () => {
  it('round-trips a saved session', () => {
    saveSession(session);
    expect(loadSession()).toEqual(session);
  });

  it('returns null when nothing is saved', () => {
    expect(loadSession()).toBeNull();
  });

  it('keeps a stopped state with its missing facts', () => {
    const stopped: SavedSession = { ...session, round: 3, state: { status: 'stopped', missing: ['State of charge'], round: 3 } };
    saveSession(stopped);
    expect(loadSession()?.state).toEqual({ status: 'stopped', missing: ['State of charge'], round: 3 });
  });

  it.each([
    ['not JSON', '{'],
    ['an older version', JSON.stringify({ ...session, version: 0 })],
    ['malformed questions', JSON.stringify({ ...session, state: { status: 'clarifying', round: 1, clarification: { reason: 'x', questions: [] } } })],
    ['an unknown status', JSON.stringify({ ...session, state: { status: 'thinking' } })],
    ['a case without facts', JSON.stringify({ ...session, operatorCase: { id: 'x', originalText: 'x', scenarios: [] } })],
  ])('discards %s', (_label, text) => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    localStorage.setItem(STORAGE_KEY, text);
    expect(loadSession()).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('clears the saved session', () => {
    saveSession(session);
    clearSession();
    expect(loadSession()).toBeNull();
  });
});

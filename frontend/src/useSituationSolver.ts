import { useEffect, useRef, useState } from 'react';
import { solveSituation, SolverUnavailableError } from './api';
import { InvalidClarificationError, parseClarificationRequest } from './clarification';
import type { ClarificationAnswer, ClarificationRequest, SolverRequest, SolverResult } from './types';

// Rounds of follow-up questions before the UI stops asking. Guards against a
// solver that keeps asking instead of answering.
export const MAX_CLARIFICATION_ROUNDS = 3;

export type SolveState =
  | { status: 'idle' }
  | { status: 'solving' }
  | { status: 'clarifying'; clarification: ClarificationRequest; round: number }
  | { status: 'solved'; result: Exclude<SolverResult, { kind: 'clarification' }> }
  | { status: 'no_match' }
  | { status: 'unavailable'; reason: string }
  | { status: 'error'; reason: string };

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error';
}

// Owns the conversation with the situation solver: the first description,
// any follow-up questions and the answers, and the final result. A new
// description always starts a fresh conversation.
export function useSituationSolver() {
  const [state, setState] = useState<SolveState>({ status: 'idle' });
  const [description, setDescription] = useState('');
  const requestRef = useRef<SolverRequest | null>(null);
  const roundRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  function run(request: SolverRequest) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    requestRef.current = request;
    setState({ status: 'solving' });
    solveSituation(request, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        if (!result) {
          setState({ status: 'no_match' });
        } else if (result.kind === 'clarification') {
          if (roundRef.current >= MAX_CLARIFICATION_ROUNDS) {
            setState({ status: 'error', reason: `The solver asked more than ${MAX_CLARIFICATION_ROUNDS} rounds of questions.` });
            return;
          }
          // Every source goes through the same shape check before rendering.
          const clarification = parseClarificationRequest(result.clarification);
          roundRef.current += 1;
          requestRef.current = { ...request, threadId: result.threadId ?? request.threadId };
          setState({ status: 'clarifying', clarification, round: roundRef.current });
        } else {
          setState({ status: 'solved', result });
        }
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof SolverUnavailableError) {
          setState({ status: 'unavailable', reason: err.message });
          return;
        }
        if (err instanceof InvalidClarificationError) {
          console.error('Solver returned malformed follow-up questions:', err);
          setState({ status: 'error', reason: 'The solver returned follow-up questions the workspace cannot show.' });
          return;
        }
        console.error('Error solving situation:', err);
        setState({ status: 'error', reason: errorMessage(err) });
      });
  }

  function describe(text: string) {
    roundRef.current = 0;
    setDescription(text);
    run({ description: text, threadId: null, answers: [] });
  }

  // Question IDs are only unique within a round, so answers are matched by
  // round and ID: resubmitting a round replaces that round's answers, while a
  // later round reusing an ID keeps the earlier answer.
  function answer(answers: ClarificationAnswer[]) {
    const current = requestRef.current;
    if (!current) return;
    const key = (item: ClarificationAnswer) => `${item.round}:${item.questionId}`;
    const answered = new Set(answers.map(key));
    run({ ...current, answers: [...current.answers.filter((item) => !answered.has(key(item))), ...answers] });
  }

  function retry() {
    if (requestRef.current) run(requestRef.current);
  }

  function cancel() {
    controllerRef.current?.abort();
    requestRef.current = null;
    roundRef.current = 0;
    setState({ status: 'idle' });
  }

  return { state, description, describe, answer, retry, cancel };
}

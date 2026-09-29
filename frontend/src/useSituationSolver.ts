import { useEffect, useRef, useState } from 'react';
import { solveSituation, SolverUnavailableError, startCase } from './api';
import type { Extraction } from './api';
import { applyAnswers, caseSummaryText, newCase, readyForEvaluation, setCaseFact } from './case';
import { clearSession, loadSession, saveSession, SESSION_VERSION } from './caseStore';
import { InvalidClarificationError, parseClarificationRequest } from './clarification';
import { resolveDispatchDownQuestion } from './scenarios';
import type { FactValue, OperatorCase } from './case';
import type { SavedSession, SavedState } from './caseStore';
import type { ClarificationAnswer, ClarificationRequest, SolverRequest, SolverResult } from './types';

// Rounds of follow-up questions before the UI stops asking. Guards against a
// solver that keeps asking instead of answering.
export const MAX_CLARIFICATION_ROUNDS = 3;

export type SolveState =
  | { status: 'idle' }
  // Turning the description into a case to review.
  | { status: 'intake' }
  // The operator checks the extracted facts and supplies missing ones before
  // anything is evaluated.
  | { status: 'reviewing'; extraction: Extraction }
  | { status: 'solving' }
  | { status: 'clarifying'; clarification: ClarificationRequest; round: number }
  // The solver still needs facts after the last allowed round. No
  // recommendation is made; `missing` names what it still asks for.
  | { status: 'stopped'; missing: string[]; round: number }
  | { status: 'solved'; result: Exclude<SolverResult, { kind: 'clarification' }> }
  | { status: 'no_match' }
  | { status: 'unavailable'; reason: string }
  | { status: 'error'; reason: string };

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error';
}

// What the solver still asks for: its required questions, or every question
// when none is marked required.
function stillMissing(clarification: ClarificationRequest): string[] {
  const required = clarification.questions.filter((question) => question.required);
  return (required.length ? required : clarification.questions).map((question) => question.prompt);
}

function restoredState(saved: SavedState): SolveState {
  return saved.status === 'pending' ? { status: 'solving' } : saved;
}

function savedState(state: SolveState): SavedState {
  if (state.status === 'reviewing' || state.status === 'clarifying' || state.status === 'stopped' || state.status === 'solved') return state;
  return { status: 'pending' };
}

// Owns one operator case from the first description to the result: intake
// and fact review, then the solver conversation (follow-up questions,
// answers, result). Answers and corrections are saved into the case, and the
// case is kept in localStorage so a reload resumes it. A new description
// always starts a fresh case. Dispatch-down risk questions skip the review:
// they need no case facts.
export function useSituationSolver() {
  const [saved] = useState<SavedSession | null>(loadSession);
  const [state, setState] = useState<SolveState>(() => (saved ? restoredState(saved.state) : { status: 'idle' }));
  const [description, setDescription] = useState(saved?.request.description ?? '');
  const [operatorCase, setOperatorCase] = useState<OperatorCase | null>(saved?.operatorCase ?? null);
  const requestRef = useRef<SolverRequest | null>(saved?.request ?? null);
  const roundRef = useRef(saved?.round ?? 0);
  const caseRef = useRef<OperatorCase | null>(saved?.operatorCase ?? null);
  const controllerRef = useRef<AbortController | null>(null);

  function persist(next: SolveState) {
    const request = requestRef.current;
    const current = caseRef.current;
    if (!request || !current) return;
    saveSession({ version: SESSION_VERSION, request, round: roundRef.current, operatorCase: current, state: savedState(next) });
  }

  function show(next: SolveState) {
    setState(next);
    persist(next);
  }

  function updateCase(next: OperatorCase) {
    caseRef.current = next;
    setOperatorCase(next);
  }

  function run(request: SolverRequest) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    requestRef.current = request;
    show({ status: 'solving' });
    solveSituation(request, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        if (!result) {
          show({ status: 'no_match' });
        } else if (result.kind === 'clarification') {
          // Every source goes through the same shape check before rendering.
          const clarification = parseClarificationRequest(result.clarification);
          requestRef.current = { ...request, threadId: result.threadId ?? request.threadId };
          if (roundRef.current >= MAX_CLARIFICATION_ROUNDS) {
            show({ status: 'stopped', missing: stillMissing(clarification), round: roundRef.current });
            return;
          }
          roundRef.current += 1;
          show({ status: 'clarifying', clarification, round: roundRef.current });
        } else {
          show({ status: 'solved', result });
        }
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof SolverUnavailableError) {
          show({ status: 'unavailable', reason: err.message });
          return;
        }
        if (err instanceof InvalidClarificationError) {
          console.error('Solver returned malformed follow-up questions:', err);
          show({ status: 'error', reason: 'The solver returned follow-up questions the workspace cannot show.' });
          return;
        }
        console.error('Error solving situation:', err);
        show({ status: 'error', reason: errorMessage(err) });
      });
  }

  // A case saved while a request was in flight runs that request again.
  useEffect(() => {
    if (saved?.state.status === 'pending') run(saved.request);
    return () => controllerRef.current?.abort();
    // Runs once on mount with the case loaded from storage.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function describe(text: string, comparisonText: string | null = null) {
    controllerRef.current?.abort();
    roundRef.current = 0;
    setDescription(text);
    const request: SolverRequest = { description: text, threadId: null, answers: [] };
    requestRef.current = request;
    // The previous case is replaced, so a reload during intake starts clean.
    clearSession();
    updateCase(newCase(text, new Date().toISOString()));
    if (!comparisonText && resolveDispatchDownQuestion(text)) {
      run(request);
      return;
    }
    const controller = new AbortController();
    controllerRef.current = controller;
    setState({ status: 'intake' });
    startCase(text, comparisonText, controller.signal)
      .then(({ operatorCase: extracted, extraction }) => {
        if (controller.signal.aborted) return;
        updateCase(extracted);
        show({ status: 'reviewing', extraction });
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        console.error('Error starting case:', err);
        show({ status: 'error', reason: errorMessage(err) });
      });
  }

  // Sends the reviewed case to the solver. Refuses while a required fact is
  // missing: a guessed fact could produce the wrong recommendation.
  function evaluate() {
    const current = caseRef.current;
    if (!current || !readyForEvaluation(current)) return;
    roundRef.current = 0;
    run({ description: current.originalText, threadId: null, answers: [], caseSummary: caseSummaryText(current) });
  }

  // Question IDs are only unique within a round, so answers are matched by
  // round and ID: resubmitting a round replaces that round's answers, while a
  // later round reusing an ID keeps the earlier answer.
  function answer(answers: ClarificationAnswer[]) {
    const current = requestRef.current;
    if (!current) return;
    if (state.status === 'clarifying' && caseRef.current) {
      updateCase(applyAnswers(caseRef.current, state.clarification.questions, answers, new Date().toISOString()));
    }
    const key = (item: ClarificationAnswer) => `${item.round}:${item.questionId}`;
    const answered = new Set(answers.map(key));
    run({ ...current, answers: [...current.answers.filter((item) => !answered.has(key(item))), ...answers] });
  }

  // The operator overrides a fact. The case keeps the old value in history.
  function correct(id: string, value: FactValue, unit: string | null = null) {
    if (!caseRef.current) return;
    updateCase(setCaseFact(caseRef.current, id, value, unit, new Date().toISOString()));
    persist(state);
  }

  function retry() {
    if (requestRef.current) run(requestRef.current);
  }

  function cancel() {
    controllerRef.current?.abort();
    requestRef.current = null;
    roundRef.current = 0;
    caseRef.current = null;
    setOperatorCase(null);
    setDescription('');
    clearSession();
    setState({ status: 'idle' });
  }

  return { state, description, operatorCase, describe, evaluate, answer, correct, retry, cancel };
}

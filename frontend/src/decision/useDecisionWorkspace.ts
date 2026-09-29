import { useRef, useState } from 'react';
import { assessDecision } from './api';
import { hintsFor } from './scope';
import type { AssessmentRequest } from './api';
import type { Assessment, BindingCondition, OperatorEdit, Plan, PlanStep, SituationFact, ViewMode } from './types';

export type AssessState =
  | { status: 'idle' }
  | { status: 'assessing' }
  | { status: 'ready'; assessment: Assessment }
  | { status: 'unavailable'; reason: string }
  | { status: 'error'; reason: string };

// Owns one decision case: the reviewed conditions, fact edits and plan
// changes the operator makes, and the backend assessment. Any change bumps
// the revision; the assessment is stale until it is rerun at that revision.
export function useDecisionWorkspace() {
  const [state, setState] = useState<AssessState>({ status: 'idle' });
  const [view, setView] = useState<ViewMode>('national');
  const [siteId, setSiteId] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [conditions, setConditions] = useState<BindingCondition[]>([]);
  const [facts, setFacts] = useState<SituationFact[]>([]);
  const [edits, setEdits] = useState<OperatorEdit[]>([]);
  const [alternative, setAlternative] = useState<Plan | null>(null);
  const [revision, setRevision] = useState(0);
  const [assessedRevision, setAssessedRevision] = useState<number | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const stale = state.status === 'ready' && assessedRevision !== revision;

  function bump() {
    setRevision((value) => value + 1);
  }

  async function run(request: AssessmentRequest, atRevision: number) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState({ status: 'assessing' });
    try {
      const result = await assessDecision(request, controller.signal);
      if (controller.signal.aborted) return;
      if (result.status === 'unavailable') {
        setState({ status: 'unavailable', reason: result.reason });
        return;
      }
      const { assessment } = result;
      setState({ status: 'ready', assessment });
      setFacts(assessment.facts);
      setConditions(assessment.conditions);
      setAlternative(assessment.alternative);
      setAssessedRevision(atRevision);
    } catch (error) {
      if (controller.signal.aborted) return;
      console.error('Assessment failed:', error);
      setState({ status: 'error', reason: error instanceof Error ? error.message : 'Unknown error' });
    }
  }

  function request(overrides: Partial<AssessmentRequest> = {}): AssessmentRequest {
    return { description, view, siteId, conditions, facts, edits, alternative, ...overrides };
  }

  // The operator's own words go to the assessment as typed. Scenario hints
  // read from the text only tell it which locked families to check.
  function assess(nextDescription: string) {
    setDescription(nextDescription);
    const { conditions: hinted } = hintsFor(nextDescription);
    setConditions(hinted);
    setEdits([]);
    setAlternative(null);
    void run(request({ description: nextDescription, conditions: hinted, facts: [], edits: [], alternative: null }), revision);
  }

  function rerun() {
    void run(request(), revision);
  }

  function changeView(next: ViewMode, nextSiteId: string | null = null) {
    setView(next);
    setSiteId(next === 'site' ? nextSiteId : null);
    bump();
  }

  function editFact(id: string, value: number | string | null) {
    const at = new Date().toISOString();
    const previous = facts.find((fact) => fact.id === id);
    if (!previous) return;
    // Keep the original value, even when it was missing, across later edits.
    const firstEdit = !edits.some((edit) => edit.factId === id);
    setEdits((list) => [...list, { factId: id, label: previous.label, from: previous.value, to: value, at }]);
    // An operator value is current but still entered by the operator; the
    // origin keeps it distinct from a measured feed.
    setFacts((current) => current.map((fact) => (fact.id === id
      ? { ...fact, value, origin: 'operator', source: 'Operator', timestamp: at, state: 'current', conflictNote: null, editedFrom: firstEdit ? fact.value : fact.editedFrom }
      : fact)));
    bump();
  }

  // Starts from the proposal the first time so the original stays for
  // comparison.
  function editAlternativeStep(stepId: string, changes: Partial<PlanStep>) {
    setAlternative((current) => {
      const base = current ?? (state.status === 'ready' ? copyAsAlternative(state.assessment.proposed) : null);
      if (!base) return current;
      return { ...base, steps: base.steps.map((step) => (step.id === stepId ? { ...step, ...changes } : step)) };
    });
    bump();
  }

  function setAlternativePlan(plan: Plan | null) {
    setAlternative(plan);
    bump();
  }

  function reset() {
    controllerRef.current?.abort();
    setState({ status: 'idle' });
    setConditions([]);
    setFacts([]);
    setEdits([]);
    setAlternative(null);
    setAssessedRevision(null);
  }

  return {
    state, stale, view, siteId, description, conditions, facts, edits, alternative,
    assess, rerun, changeView, editFact, editAlternativeStep, setAlternativePlan, reset,
  };
}

export function copyAsAlternative(plan: Plan | null): Plan | null {
  if (!plan) return null;
  return {
    ...plan,
    id: 'plan-operator',
    name: 'Operator alternative',
    origin: 'operator',
    label: 'insufficient_evidence',
    labelReason: 'Not assessed yet.',
    steps: plan.steps.map((step) => ({ ...step })),
  };
}

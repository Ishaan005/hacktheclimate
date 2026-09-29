import { USE_FIXTURE } from '../mode';
import { fromBackendAssessment, isBackendAssessment, toBackendRequest } from './backend';
import { fixtureAssessment } from './fixture';
import { siteById } from './sites';
import { fixtureAssessmentForSite } from './siteFixtures';
import { hintsFor } from './scope';
import type { Assessment, BindingCondition, OperatorEdit, Plan, SituationFact, ViewMode } from './types';

export type AssessmentRequest = {
  description: string;
  view: ViewMode;
  siteId: string | null;
  conditions: BindingCondition[];
  facts: SituationFact[];
  edits: OperatorEdit[];
  alternative: Plan | null;
};

export type AssessmentResponse =
  | { status: 'ok'; assessment: Assessment }
  | { status: 'unavailable'; reason: string };

const ENDPOINT = '/v1/workspace/assess';

// Fixture mode returns the demonstration assessment with the operator's
// conditions, facts and alternative carried over. It does not recompute any
// safety result: an operator alternative stays unassessed until a backend
// evaluates it.
function fixtureResponse(request: AssessmentRequest): AssessmentResponse {
  const site = request.view === 'national' ? undefined : siteById(request.siteId);
  const base = request.view === 'national' ? fixtureAssessment : fixtureAssessmentForSite(request.siteId ?? '');
  if (!base || (request.view !== 'national' && !site)) {
    return { status: 'unavailable', reason: 'Choose a plant before assessing this view.' };
  }
  const context = {
    ...base.context,
    view: request.view,
    siteId: request.view === 'national' ? null : request.siteId,
    location: site?.name ?? 'All-island',
    siteConnection: site?.connection ?? null,
    limitingRoute: site?.limitingRoute ?? base.context.limitingRoute,
  };
  // No locked scenario in the text: the fixture has nothing to show but the
  // intake state.
  if (!request.conditions.length) {
    const { causeUnknown } = hintsFor(request.description);
    return { status: 'ok', assessment: { ...base, context, conditions: [], causeUnknown, proposed: null, alternative: null, edits: [] } };
  }
  const facts = request.facts.length ? request.facts : base.facts;
  return {
    status: 'ok',
    assessment: {
      ...base,
      context,
      conditions: request.conditions,
      facts,
      edits: request.edits,
      alternative: request.alternative
        ? { ...request.alternative, label: 'insufficient_evidence', labelReason: 'Fixture mode cannot assess an operator alternative.' }
        : null,
    },
  };
}

export async function assessDecision(request: AssessmentRequest, signal?: AbortSignal): Promise<AssessmentResponse> {
  if (USE_FIXTURE) return fixtureResponse(request);
  let response: Response;
  try {
    response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toBackendRequest(request)),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    return { status: 'unavailable', reason: 'The API server could not be reached.' };
  }
  if (response.status === 404 || response.status === 405 || response.status === 503) {
    return {
      status: 'unavailable',
      reason: `The assessment API is unavailable (${ENDPOINT} returned HTTP ${response.status}).`,
    };
  }
  if (!response.ok) throw new Error(`${ENDPOINT} returned HTTP ${response.status}`);
  const body: unknown = await response.json();
  if (!isBackendAssessment(body)) throw new Error(`${ENDPOINT} returned an invalid assessment`);
  return { status: 'ok', assessment: fromBackendAssessment(body, request) };
}

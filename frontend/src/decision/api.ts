import { USE_FIXTURE } from '../mode';
import { fixtureAssessment } from './fixture';
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

const ENDPOINT = '/v1/decision/assess';

// Fixture mode returns the demonstration assessment with the operator's
// conditions, facts and alternative carried over. It does not recompute any
// safety result: an operator alternative stays unassessed until a backend
// evaluates it.
function fixtureResponse(request: AssessmentRequest): AssessmentResponse {
  const base = fixtureAssessment;
  const facts = request.facts.length ? request.facts : base.facts;
  return {
    status: 'ok',
    assessment: {
      ...base,
      context: {
        ...base.context,
        view: request.view,
        siteId: request.siteId,
        location: request.view === 'site' ? 'Wind Farm A (demonstration site)' : 'All-island',
        siteConnection: request.view === 'site' ? 'Cashla 110 kV busbar' : null,
      },
      conditions: request.conditions.length ? request.conditions : base.conditions,
      facts,
      edits: request.edits,
      alternative: request.alternative
        ? { ...request.alternative, label: 'insufficient_evidence', labelReason: 'Fixture mode cannot assess an operator alternative.' }
        : null,
    },
  };
}

// The backend assessment route (POST /v1/decision/assess) is not built yet.
// Until it is, live mode says so instead of showing any result: safety
// results must come from a validated backend assessment, never the browser.
export async function assessDecision(request: AssessmentRequest, signal?: AbortSignal): Promise<AssessmentResponse> {
  if (USE_FIXTURE) return fixtureResponse(request);
  let response: Response;
  try {
    response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    return { status: 'unavailable', reason: 'The API server could not be reached.' };
  }
  if (response.status === 404 || response.status === 405 || response.status === 503) {
    return {
      status: 'unavailable',
      reason: `The API has no assessment route yet (${ENDPOINT} returned HTTP ${response.status}). Start the UI with VITE_API_MODE=fixture to see the demonstration assessment.`,
    };
  }
  if (!response.ok) throw new Error(`${ENDPOINT} returned HTTP ${response.status}`);
  return { status: 'ok', assessment: (await response.json()) as Assessment };
}

import { illustrativeScenarios } from './fixtures/illustrativeScenarios';
import { fixtureOperatorView, fixtureOutages, fixtureScenario } from './fixtures/operatorView';
import { namedTarget, resolveDispatchDownQuestion, resolveFixtureSolver } from './scenarios';
import type { ClarificationAnswer, NetworkDecision, OperatorView, ReviewedOutageOption, SolverRequest, SolverResult } from './types';

import { USE_FIXTURE } from './mode';

export { USE_FIXTURE };
type BackendOperatorResponse = Omit<NetworkDecision, 'rows'> & { forecast: NetworkDecision['rows'] };

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function mapOperatorResponse(raw: BackendOperatorResponse): OperatorView {
  const issued = raw.health.forecast_issue_time;
  return {
    forecast: {
      output_type: 'forecast',
      status: 'ok',
      model_version: raw.health.forecast_source,
      target: 'constraint_mwh',
      event_definition: 'Upstream-defined national constraint event',
      issued_at: issued,
      intervals: raw.forecast.map((row) => ({
        target_timestamp: row.valid_time,
        decision_timestamp: issued,
        horizon_hours: (Date.parse(row.valid_time) - Date.parse(issued)) / 3_600_000,
        event_probability: row.constraint_probability,
        expected_constraint_mwh: row.expected_constraint_mwh,
        expected_constraint_mwh_lower: null,
        expected_constraint_mwh_upper: null,
      })),
      decision_context: [],
      evaluation: {
        calibration_status: 'unknown', test_period: null, event_prevalence: null,
        pr_auc: null, interval_coverage: null, interval_nominal: null,
        beats_baseline: null, baseline: null,
        note: 'No validated point-in-time national forecast evaluation is attached.',
      },
      sources: [{
        source: raw.health.forecast_source,
        vintage: issued,
        retrieved_at: null,
        note: 'Supplied upstream forecast; the API checks its issue time but does not validate model accuracy.',
      }],
    },
    scenario: null,
    decision: {
      rows: raw.forecast,
      network: raw.network,
      actions: raw.actions,
      recommendation: raw.recommendation,
      health: raw.health,
    },
  };
}

export async function fetchOperatorView(outageId: string | null, signal?: AbortSignal): Promise<OperatorView> {
  if (USE_FIXTURE) {
    if (!outageId) return fixtureOperatorView;
    if (outageId === fixtureScenario.report.outage_review.annual.outage_id) {
      return { ...fixtureOperatorView, scenario: fixtureScenario };
    }
    return {
      ...fixtureOperatorView,
      scenario: {
        output_type: 'planning_scenario',
        status: 'unavailable',
        reason: 'No reviewed planning-case match for this outage.',
      },
    };
  }
  return mapOperatorResponse(await getJson<BackendOperatorResponse>('/v1/operator/view', signal));
}

export async function fetchReviewedOutages(signal?: AbortSignal): Promise<ReviewedOutageOption[]> {
  if (USE_FIXTURE) return fixtureOutages;
  void signal;
  return [];
}

// Thrown while the LLM solver is not reachable (chat not configured, or the
// API is down), so the UI can say so instead of showing a generic error.
export class SolverUnavailableError extends Error {}

// Tools whose result is the national dispatch-down forecast. When the
// assistant used one, the real forecast view is shown beside its reply.
const DISPATCH_DOWN_TOOLS = new Set(['get_dispatch_down_forecast', 'get_dispatch_down_day']);

type ChatResponse = { thread_id: string; reply: string; tools_used: string[]; model: string };

// The chat route takes one message per turn. Follow-up answers are sent as a
// short labelled list on the same thread; the first turn is the description.
export function chatMessage(request: SolverRequest): string {
  if (!request.answers.length) return request.description;
  const lines = request.answers.map((answer: ClarificationAnswer) => {
    const value = answer.value === null ? '(left blank)' : Array.isArray(answer.value) ? answer.value.join(', ') : String(answer.value);
    return `- round ${answer.round}, ${answer.questionId}: ${value}`;
  });
  return [`Answers to your follow-up questions about: ${request.description}`, ...lines].join('\n');
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
  } catch {
    // Not JSON; fall through to the status line.
  }
  return `/v1/chat returned HTTP ${response.status}`;
}

// Turns an operator's situation description into one solver result.
// Fixture mode matches keywords against illustrative data. Live mode sends
// the description to the LangGraph assistant (POST /v1/chat), which calls the
// real forecast tools and ends with its select_action recommendation. If the
// assistant is not configured (503) or the API cannot be reached,
// dispatch-down questions still open the real dispatch-down view.
export async function solveSituation(request: SolverRequest, signal?: AbortSignal): Promise<SolverResult | null> {
  if (USE_FIXTURE) return resolveFixtureSolver(request, illustrativeScenarios);
  const selectedTarget = namedTarget(request.description);
  let response: Response;
  try {
    response = await fetch('/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: chatMessage(request), thread_id: request.threadId, selected_target: selectedTarget }),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    const fallback = resolveDispatchDownQuestion(request.description);
    if (fallback) return fallback;
    throw new SolverUnavailableError('The API server could not be reached.');
  }
  if (response.status === 503 || response.status === 404) {
    // 503: Azure OpenAI not configured. 404: chat extras not installed.
    const fallback = resolveDispatchDownQuestion(request.description);
    if (fallback) return fallback;
    throw new SolverUnavailableError(await errorDetail(response));
  }
  if (!response.ok) throw new Error(await errorDetail(response));
  const body = (await response.json()) as ChatResponse;
  const usedForecast = body.tools_used.some((name) => DISPATCH_DOWN_TOOLS.has(name));
  return {
    kind: 'assistant_reply',
    reply: { threadId: body.thread_id, text: body.reply, toolsUsed: body.tools_used, model: body.model },
    target: usedForecast ? selectedTarget : null,
  };
}

import { illustrativeScenarios } from './fixtures/illustrativeScenarios';
import { fixtureOperatorView, fixtureOutages, fixtureScenario } from './fixtures/operatorView';
import { resolveFixtureSolver } from './scenarios';
import type { NetworkDecision, OperatorView, ReviewedOutageOption, SolverRequest, SolverResult } from './types';

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

// Thrown while the LLM scenario solver is not connected, so the UI can say so
// instead of showing a generic error.
export class SolverUnavailableError extends Error {}

// Turns an operator's situation description, plus any answers to earlier
// follow-up questions, into one solver result: a workspace scenario, a
// dispatch-down risk view or more questions. Null means no match.
// Fixture mode matches keywords; live mode waits for the LLM solver endpoint,
// which is not linked yet. useSituationSolver shape-checks any follow-up
// questions before they render.
export async function solveSituation(request: SolverRequest, signal?: AbortSignal): Promise<SolverResult | null> {
  if (USE_FIXTURE) return resolveFixtureSolver(request, illustrativeScenarios);
  void signal;
  throw new SolverUnavailableError('The scenario solver is not connected yet.');
}

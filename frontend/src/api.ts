import { fixtureOperatorView, fixtureOutages, fixtureScenario } from './fixtures/operatorView';
import type { OperatorView, ReviewedOutageOption } from './types';

// Until the combined forecast/scenario API lands (issue #14), the UI runs on
// the fixture. Set VITE_API_MODE=live in frontend/.env.local to call the
// backend instead. Both endpoint paths are PROPOSED; no such routes exist in
// backend/app yet.
export const USE_FIXTURE = import.meta.env.VITE_API_MODE !== 'live';

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    throw new Error(`${path} returned HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
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
  const query = outageId ? `?outage_id=${encodeURIComponent(outageId)}` : '';
  return getJson<OperatorView>(`/v1/operator/view${query}`, signal);
}

export async function fetchReviewedOutages(signal?: AbortSignal): Promise<ReviewedOutageOption[]> {
  if (USE_FIXTURE) return fixtureOutages;
  return getJson<ReviewedOutageOption[]>('/v1/scenario/outages', signal);
}

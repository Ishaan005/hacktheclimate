import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import ForecastPanel from './components/ForecastPanel';
import NetworkDecisionPanel from './components/NetworkDecisionPanel';
import ScenarioPanel from './components/ScenarioPanel';
import { COPY, FORBIDDEN_PHRASES, STATE_COPY } from './copy';
import { mapOperatorResponse } from './api';
import { fixtureOutages } from './fixtures/operatorView';
import type { NationalForecast, NetworkDecision, SafetyCheck } from './types';

// Structure-only forecast: no forecast exists yet (issue #8), so every value
// is null. This checks the normal-state labels without inventing numbers.
// Horizons run 1 h to 24 h in half-hour steps (47 intervals).
const DECISION = Date.parse('2026-01-01T00:00:00Z');
const emptyForecast: NationalForecast = {
  output_type: 'forecast',
  status: 'ok',
  model_version: 'structure-test',
  target: 'constraint_mwh',
  event_definition: 'constraint_mwh above the API-defined threshold',
  issued_at: new Date(DECISION).toISOString(),
  intervals: Array.from({ length: 47 }, (_, index) => ({
    target_timestamp: new Date(DECISION + (index + 2) * 30 * 60 * 1000).toISOString(),
    decision_timestamp: new Date(DECISION).toISOString(),
    horizon_hours: (index + 2) / 2,
    event_probability: null,
    expected_constraint_mwh: null,
    expected_constraint_mwh_lower: null,
    expected_constraint_mwh_upper: null,
  })),
  decision_context: [],
  evaluation: {
    calibration_status: 'unknown',
    test_period: null,
    event_prevalence: null,
    pr_auc: null,
    interval_coverage: null,
    interval_nominal: null,
    beats_baseline: null,
    baseline: null,
    note: null,
  },
  sources: [],
};

function expectNoForbiddenCopy() {
  const text = document.body.textContent?.toLowerCase() ?? '';
  for (const phrase of FORBIDDEN_PHRASES) {
    expect(text).not.toContain(phrase);
  }
}

describe('app page', () => {
  it('shows only the dispatch-down forecast and chart', async () => {
    render(<App />);
    expect(await screen.findByRole('region', { name: 'Next-hour dispatch-down risk' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /Dispatch-down risk through/ })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: COPY.forecastTitle })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: COPY.scenarioTitle })).not.toBeInTheDocument();
  });
});

describe('national forecast normal state', () => {
  it('labels horizon and confidence and renders missing values as gaps, not zeros', () => {
    render(<ForecastPanel forecast={emptyForecast} loading={false} error={null} />);
    const forecast = screen.getByRole('region', { name: COPY.forecastTitle });

    expect(within(forecast).getByRole('img', { name: /47 intervals, 47 unavailable/ })).toBeInTheDocument();
    expect(within(forecast).getByText(/1–24 h ahead/)).toBeInTheDocument();
    expect(within(forecast).getByRole('heading', { name: new RegExp(COPY.forecastConfidence) })).toBeInTheDocument();
    expect(within(forecast).getByText('Baseline comparison not available')).toBeInTheDocument();
    expect(forecast).toHaveTextContent(COPY.forecastScope);
    expect(forecast).not.toHaveTextContent(COPY.assetMatchConfidence);
    expectNoForbiddenCopy();
  });
});

describe('loading, error and unavailable states keep the product labels', () => {
  it('labels both panels while loading', () => {
    render(
      <>
        <ForecastPanel forecast={null} loading error={null} />
        <ScenarioPanel outages={[]} selectedOutageId={null} onSelectOutage={() => {}} scenario={null} loading error={null} />
      </>,
    );
    expect(screen.getByRole('region', { name: COPY.forecastTitle })).toHaveTextContent(COPY.forecastLoading);
    expect(screen.getByRole('region', { name: COPY.scenarioTitle })).toHaveTextContent(COPY.scenarioLoading);
  });

  it('labels both panels on error and offers a retry', () => {
    const onRetry = vi.fn();
    render(
      <>
        <ForecastPanel forecast={null} loading={false} error="HTTP 503" onRetry={onRetry} />
        <ScenarioPanel outages={[]} selectedOutageId={null} onSelectOutage={() => {}} scenario={null} loading={false} error="HTTP 503" />
      </>,
    );
    expect(screen.getByRole('region', { name: COPY.forecastTitle })).toHaveTextContent(STATE_COPY.forecastErrorTitle);
    expect(screen.getByRole('region', { name: COPY.scenarioTitle })).toHaveTextContent(STATE_COPY.scenarioErrorTitle);
    fireEvent.click(screen.getByRole('button', { name: STATE_COPY.retry }));
    expect(onRetry).toHaveBeenCalledOnce();
    expectNoForbiddenCopy();
  });

  it('shows the scenario-unavailable state with its reason', () => {
    render(
      <ScenarioPanel
        outages={fixtureOutages}
        selectedOutageId={fixtureOutages[0].outage_id}
        onSelectOutage={() => {}}
        scenario={{ output_type: 'planning_scenario', status: 'unavailable', reason: 'Outage audit has no reviewed asset match.' }}
        loading={false}
        error={null}
      />,
    );
    const scenario = screen.getByRole('region', { name: COPY.scenarioTitle });
    expect(scenario).toHaveTextContent(STATE_COPY.scenarioUnavailableTitle);
    expect(scenario).toHaveTextContent('Outage audit has no reviewed asset match.');
  });
});

describe('live network and action screen', () => {
  it('shows unsupported checks and never turns an unknown action into a recommendation', () => {
    const unknown: SafetyCheck = { status: 'UNKNOWN', reason: 'No supported calculation.', evidence: null };
    const decision: NetworkDecision = {
      rows: [{
        valid_time: '2026-09-29T01:00:00Z', constraint_probability: 0.5,
        expected_constraint_mwh: 20,
        network: {
          scenario: 'screened-n-1', worst_asset: '1:2:1',
          max_dc_loading_proxy_pct: 88, security_event: false,
          safety: {
            overall: 'UNKNOWN', recommendable: false, thermal: unknown,
            islanding: unknown, snsp: unknown, voltage: unknown,
            inertia: unknown, rocof: unknown,
          },
        },
      }],
      network: {
        case_scenario_date: '2024-07-01',
        planned_outage: { asset_type: 'branch', asset_id: '1642:2522:1' },
        scope: 'TYTFS planning-case DC scenario screen',
      },
      actions: [{ action_id: 'flex-1', power_mw: 10, safety_overall: 'UNKNOWN',
        modeled_capture_upper_bound_mwh: 5, expected_avoided_constraint_mwh: null }],
      recommendation: null,
      health: {
        status: 'incomplete', forecast_issue_time: '2026-09-28T18:00:00Z',
        forecast_source: 'synthetic-test', missing_inputs: ['voltage evidence'],
        unsupported_safety_checks: ['voltage', 'inertia', 'rocof'],
        recommendation_reason: 'No fully PASS action is available.',
      },
    };
    const { rows, ...rest } = decision;
    const mapped = mapOperatorResponse({ ...rest, forecast: rows });
    expect(mapped.forecast.status).toBe('ok');
    if (mapped.forecast.status === 'ok') {
      expect(mapped.forecast.intervals[0].expected_constraint_mwh).toBe(20);
      expect(mapped.forecast.evaluation.calibration_status).toBe('unknown');
    }
    render(<NetworkDecisionPanel decision={mapped.decision ?? null} loading={false} error={null} onRetry={() => {}} />);
    const panel = screen.getByRole('region', { name: 'TYTFS network and safety screen' });
    expect(panel).toHaveTextContent('Safety screen: UNKNOWN');
    expect(panel).toHaveTextContent('flex-1: 10.0 MW · safety UNKNOWN');
    expect(panel).toHaveTextContent('Recommendation: none.');
  });
});

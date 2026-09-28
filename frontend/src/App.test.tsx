import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import ForecastPanel from './components/ForecastPanel';
import ScenarioPanel from './components/ScenarioPanel';
import { COPY, FORBIDDEN_PHRASES, STATE_COPY } from './copy';
import { fixtureOutages } from './fixtures/operatorView';
import type { NationalForecast } from './types';

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

describe('operator screen with the representative response', () => {
  it('labels both products and shows the forecast as unavailable', async () => {
    render(<App />);
    const forecast = screen.getByRole('region', { name: COPY.forecastTitle });
    const scenario = screen.getByRole('region', { name: COPY.scenarioTitle });

    expect(await within(forecast).findByText(/issue #8/)).toBeInTheDocument();
    expect(within(forecast).queryByRole('img')).not.toBeInTheDocument();
    expect(within(scenario).getByText(STATE_COPY.scenarioEmptyTitle)).toBeInTheDocument();
    expect(within(forecast).getByText(STATE_COPY.forecastUnavailableConsequence)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Current picture' })).toHaveTextContent('No forecast yet');
    expectNoForbiddenCopy();
  });

  it('shows the Cashla–Flagford intact vs outage comparison from the network report', async () => {
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Reviewed outage'), {
      target: { value: fixtureOutages[0].outage_id },
    });
    const scenario = screen.getByRole('region', { name: COPY.scenarioTitle });

    expect(await within(scenario).findByRole('heading', { name: new RegExp(COPY.assetMatchConfidence) })).toBeInTheDocument();
    expect(within(scenario).getByText('Reviewed match')).toBeInTheDocument();
    const table = within(scenario).getByRole('table');
    expect(within(table).getByText('157.0 MW')).toBeInTheDocument();
    expect(within(table).getByLabelText('−48.7 MW compared with all equipment in service')).toBeInTheDocument();
    expect(within(table).getByText('20.6%')).toBeInTheDocument();
    // Plain-language finding and summary strip are derived from the same report.
    expect(within(scenario).getByText(/reduces flow on the monitored branch by 48\.7 MW/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Current picture' })).toHaveTextContent('Peak 20.6% of rate A');
    // The forecast stays unavailable while the scenario renders.
    expect(screen.getByRole('region', { name: COPY.forecastTitle })).toHaveTextContent(/issue #8/);
    expectNoForbiddenCopy();
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

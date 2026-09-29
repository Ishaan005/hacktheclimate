import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { fixtureAssessment } from '../../decision/fixture';
import type { OutcomeState } from '../../decision/types';
import ComparisonPanel from './ComparisonPanel';

const { outcomes, benefits } = fixtureAssessment;

function renderPanel(overrides: { outcomes?: OutcomeState[]; stale?: boolean } = {}) {
  return render(
    <ComparisonPanel outcomes={overrides.outcomes ?? outcomes} benefits={benefits} view="national" stale={overrides.stale ?? false} />,
  );
}

function headerTexts(): string[] {
  const head = screen.getByRole('table').querySelector('thead') as HTMLElement;
  return within(head).getAllByRole('columnheader').map((cell) => cell.textContent ?? '');
}

function card(label: string): HTMLElement {
  return screen.getByText(label, { selector: 'dt' }).closest('.established-card') as HTMLElement;
}

describe('ComparisonPanel', () => {
  it('shows evaluated plan columns in order and marks the baseline', () => {
    renderPanel();
    const headers = headerTexts().slice(1);
    expect(headers).toHaveLength(3);
    expect(headers[0]).toMatch(/^Current plan/);
    expect(headers[1]).toMatch(/^No new instruction/);
    expect(headers[1]).toMatch(/Baseline for claimed improvements/);
    expect(headers[2]).toMatch(/^Proposed plan/);
    expect(headers.join(' ')).not.toMatch(/Operator alternative/);
  });

  it('omits an unevaluated operator alternative', () => {
    renderPanel();
    expect(screen.queryByRole('columnheader', { name: /Operator alternative/ })).not.toBeInTheDocument();
  });

  it('never shows a missing value as zero MWh', () => {
    renderPanel();
    expect(screen.queryByText(/^0 MWh/)).not.toBeInTheDocument();
    expect(screen.queryByRole('rowheader', { name: 'Curtailed (MWh)' })).not.toBeInTheDocument();
  });

  it('shows constrained energy without an invented curtailed value', () => {
    renderPanel();
    const constrained = screen.getByRole('rowheader', { name: 'Constrained (MWh)' }).closest('tr') as HTMLElement;
    expect(constrained).toBeInTheDocument();
    expect(within(constrained).getByText('62 MWh')).toBeInTheDocument();
    expect(within(constrained).getByText('(40–90)')).toBeInTheDocument();
  });

  it('keeps an explicit zero when curtailment is actually supplied', () => {
    const withZero = outcomes.map((outcome) => outcome.column === 'current'
      ? { ...outcome, curtailedMwh: { ...outcome.curtailedMwh, value: 0, source: 'Reviewed source' } }
      : outcome);
    renderPanel({ outcomes: withZero });
    const curtailed = screen.getByRole('rowheader', { name: 'Curtailed (MWh)' }).closest('tr') as HTMLElement;
    expect(within(curtailed).getByText('0 MWh')).toBeInTheDocument();
  });

  it('puts safety rows above dispatch-down rows', () => {
    renderPanel();
    const rows = screen.getAllByRole('rowheader').map((cell) => cell.textContent);
    expect(rows.indexOf('Safety result')).toBeLessThan(rows.indexOf('Constrained (MWh)'));
    expect(rows.indexOf('Time to breach (min)')).toBeLessThan(rows.indexOf('Constrained (MWh)'));
  });

  it('does not let a plan with unknown safety claim its benefits', () => {
    renderPanel();
    const avoided = card('Avoided dispatch-down');
    expect(avoided).toHaveTextContent('Cannot be claimed: required safety check is Unknown');
    // The number stays visible as context.
    expect(within(avoided).getByText('40 MWh')).toBeInTheDocument();
    expect(avoided).toHaveTextContent('A MW × time upper bound is not proven saved energy.');
  });

  it('allows benefits once the proposed plan passes safety', () => {
    const passing = outcomes.map((outcome) => (outcome.column === 'proposed' ? { ...outcome, safety: 'pass' as const } : outcome));
    renderPanel({ outcomes: passing });
    expect(card('Avoided dispatch-down')).not.toHaveTextContent('Cannot be claimed');
  });

  it('shows available national context without empty site and money cards', () => {
    renderPanel();
    expect(screen.queryByText('Site dispatch-down risk')).not.toBeInTheDocument();
    expect(screen.getByText('National context only, not a site outcome')).toBeInTheDocument();
    expect(screen.queryByText('Gross market opportunity')).not.toBeInTheDocument();
  });

  it('warns when a column uses a different window', () => {
    const shifted = outcomes.map((outcome) => (outcome.column === 'proposed' ? { ...outcome, windowEnd: '2026-01-24T19:00:00Z' } : outcome));
    renderPanel({ outcomes: shifted });
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Proposed plan');
    expect(alert).toHaveTextContent('not comparable');
  });

  it('has no window warning when all columns match, and shows the stale note', () => {
    renderPanel({ stale: true });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/Rerun the assessment/);
  });
});

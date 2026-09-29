import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { fixtureAssessment } from '../../decision/fixture';
import type { Benefits, Established, OutcomeState } from '../../decision/types';
import ComparisonPanel from './ComparisonPanel';

const { outcomes, benefits } = fixtureAssessment;

function renderPanel(overrides: { outcomes?: OutcomeState[]; benefits?: Benefits } = {}) {
  return render(
    <ComparisonPanel
      outcomes={overrides.outcomes ?? outcomes}
      benefits={overrides.benefits ?? benefits}
      view="national"
    />,
  );
}

function headerCells(): HTMLElement[] {
  const head = screen.getByRole('table').querySelector('thead') as HTMLElement;
  return within(head).getAllByRole('columnheader');
}

function card(label: string): HTMLElement {
  return screen.getByText(label, { selector: 'dt' }).closest('.established-card') as HTMLElement;
}

function row(label: string): HTMLElement {
  return screen.getByRole('rowheader', { name: label }).closest('tr') as HTMLElement;
}

const missing = (unit: string, reason: string): Established => (
  { value: null, lower: null, upper: null, unit, method: null, source: null, notEstablishedReason: reason }
);

const noBenefits: Benefits = {
  avoidedDispatchDownMwh: missing('MWh', 'No validated outcome evidence.'),
  siteRiskProbability: missing('%', 'No validated site model.'),
  siteRiskExpectedMwh: missing('MWh', 'No validated site model.'),
  nationalContext: null,
  netSystemResourceCostEur: { ...missing('EUR', 'No prices.'), perspective: null },
  grossMarketOpportunityEur: missing('EUR', 'No route.'),
  netFinancialValueEur: { ...missing('EUR', 'No revenue.'), perspective: null },
  carbonEffectTco2e: missing('tCO2e', 'Not modelled.'),
};

describe('ComparisonPanel', () => {
  it('shows the four plan columns in order and marks the baseline', () => {
    renderPanel();
    expect(screen.getByRole('heading', { level: 2, name: 'Compare outcomes' })).toBeInTheDocument();
    const headers = headerCells().slice(1).map((cell) => cell.textContent ?? '');
    expect(headers).toHaveLength(4);
    expect(headers[0]).toMatch(/^Current plan/);
    expect(headers[1]).toMatch(/^No new instruction/);
    expect(headers[1]).toMatch(/Baseline for claimed improvements/);
    expect(headers[2]).toMatch(/^Proposed plan/);
    expect(headers[3]).toMatch(/^Operator alternative/);
  });

  it('shows no reasons or footnotes for missing values', () => {
    renderPanel();
    expect(screen.queryByRole('list', { name: 'Notes' })).not.toBeInTheDocument();
    expect(document.querySelector('sup')).toBeNull();
    for (const reason of ['No operator alternative entered.', 'No new instruction.', 'No curtailment model for this window.']) {
      expect(screen.queryByText(reason)).not.toBeInTheDocument();
    }
    // A column with no plan shows a dash in each cell and nothing under its header.
    expect(headerCells()[4]).toHaveTextContent(/^Operator alternative$/);
    expect(within(row('Safety result')).getAllByText('—')).toHaveLength(1);
  });

  it('never shows a missing value as zero MWh', () => {
    renderPanel();
    expect(screen.queryByText(/^0 MWh/)).not.toBeInTheDocument();
    const curtailed = row('Curtailed (MWh)');
    expect(within(curtailed).getAllByText('Not established')).toHaveLength(4);
  });

  it('keeps constrained and curtailed as separate rows', () => {
    renderPanel();
    const constrained = row('Constrained (MWh)');
    expect(constrained).not.toBe(row('Curtailed (MWh)'));
    expect(within(constrained).getByText('62 MWh')).toBeInTheDocument();
    expect(within(constrained).getByText('(40–90)')).toBeInTheDocument();
    expect(within(constrained).getAllByText('Planning-case replay · Demonstration')).toHaveLength(3);
  });

  it('puts safety rows above dispatch-down rows', () => {
    renderPanel();
    const rows = screen.getAllByRole('rowheader').map((cell) => cell.textContent);
    expect(rows.indexOf('Safety result')).toBeLessThan(rows.indexOf('Constrained (MWh)'));
    expect(rows.indexOf('Time to breach (min)')).toBeLessThan(rows.indexOf('Constrained (MWh)'));
  });

  it('names both days for a multi-day window', () => {
    const day = outcomes.map((outcome) => ({ ...outcome, windowStart: '2026-09-29T16:30:00Z', windowEnd: '2026-09-30T16:30:00Z' }));
    renderPanel({ outcomes: day });
    const meta = document.querySelector('.panel-meta') as HTMLElement;
    expect(meta).toHaveTextContent(/29 Sept.*30 Sept/);
    expect(meta).not.toHaveTextContent('UTC UTC');
  });

  it('greys numbers that cannot be claimed without a cannot-claim message', () => {
    renderPanel();
    expect(screen.queryByText(/Cannot be claimed/)).not.toBeInTheDocument();
    const avoided = card('Avoided dispatch-down');
    expect(within(avoided).getByText('40 MWh')).toBeInTheDocument();
    expect(avoided).toHaveClass('established-card-greyed');
    expect(card('Carbon effect')).not.toHaveClass('established-card-greyed');
  });

  it('collapses benefits to one line when nothing is established and safety is unknown', () => {
    renderPanel({ benefits: noBenefits });
    expect(screen.getByText(/^Benefits not established\./)).toHaveTextContent('required safety result is Unknown');
    expect(screen.queryByText(/Cannot be claimed/)).not.toBeInTheDocument();
    const details = screen.getByText('Show benefit details').closest('details') as HTMLDetailsElement;
    expect(details).not.toHaveAttribute('open');
    expect(within(details).getByText('Avoided dispatch-down', { selector: 'dt' })).toBeInTheDocument();
  });

  it('allows benefits once the proposed plan passes safety', () => {
    const passing = outcomes.map((outcome) => (outcome.column === 'proposed' ? { ...outcome, safety: 'pass' as const } : outcome));
    renderPanel({ outcomes: passing });
    expect(screen.queryByText(/Cannot be claimed/)).not.toBeInTheDocument();
    expect(card('Avoided dispatch-down')).not.toHaveClass('established-card-greyed');
  });

  it('labels the national estimate as context when site risk is not established', () => {
    renderPanel();
    const site = card('Site dispatch-down risk');
    expect(site).toHaveTextContent('Not established');
    expect(site).toHaveTextContent('National context only, not a site outcome');
    expect(card('Gross market opportunity')).toHaveTextContent('Estimate, not TSO profit.');
  });

  it('warns when a column uses a different window', () => {
    const shifted = outcomes.map((outcome) => (outcome.column === 'proposed' ? { ...outcome, windowEnd: '2026-01-24T19:00:00Z' } : outcome));
    renderPanel({ outcomes: shifted });
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Proposed plan');
    expect(alert).toHaveTextContent('not comparable');
  });

  it('has no window warning when all columns match', () => {
    renderPanel();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});

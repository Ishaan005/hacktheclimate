import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { fixtureAssessment } from '../../decision/fixture';
import type { OutcomeState } from '../../decision/types';
import ComparisonPanel from './ComparisonPanel';

const outcomes = fixtureAssessment.outcomes;

function show(values: OutcomeState[] = outcomes) {
  return render(<ComparisonPanel outcomes={values} benefits={fixtureAssessment.benefits} view="national" families={['transmission']} />);
}

describe('outcome comparison', () => {
  it('shows two columns for the comparable energy values', () => {
    show();
    const chart = screen.getByRole('figure', { name: /20 MWh potential avoided dispatch-down/ });
    expect(within(chart).getByText('40 MWh')).toBeInTheDocument();
    expect(within(chart).getByText('20 MWh')).toBeInTheDocument();
    expect(within(chart).getByText('No input')).toBeInTheDocument();
    expect(within(chart).getByText('Proposed plan')).toBeInTheDocument();
    expect(within(chart).getByText(/potential avoided dispatch-down/)).toBeInTheDocument();
    expect(chart).not.toHaveTextContent('in this scenario');
  });

  it('only labels the reduction avoided dispatch-down after safety passes', () => {
    const passing = outcomes.map((item) => item.column === 'proposed' ? { ...item, safety: 'pass' as const } : item);
    show(passing);
    expect(screen.getByText('20 MWh avoided dispatch-down')).toBeInTheDocument();
  });

  it('keeps the three impact figures fixed and removes calculator inputs and formulas', () => {
    show();
    const impact = screen.getByRole('region', { name: 'Illustrative energy impact' });
    expect(within(impact).getByText('Gross energy value').parentElement).toHaveTextContent('€2,000');
    expect(within(impact).getByText('Illustrative saving after plan cost').parentElement).toHaveTextContent('€2,000');
    expect(within(impact).getByText('CO₂ displacement potential').parentElement).toHaveTextContent('7.0 tCO₂');
    expect(within(impact).queryByRole('spinbutton')).not.toBeInTheDocument();
    expect(within(impact).queryByRole('combobox')).not.toBeInTheDocument();
    expect(impact).not.toHaveTextContent('No input minus');
  });

  it('shows missing energy as unavailable instead of inventing a number', () => {
    const unavailable = outcomes.map((item) => item.column === 'proposed'
      ? { ...item, constrainedMwh: { ...item.constrainedMwh, value: null } } : item);
    show(unavailable);
    expect(screen.getByText('Comparable dispatch-down energy is unavailable for this case.')).toBeInTheDocument();
    const impact = screen.getByRole('region', { name: 'Illustrative energy impact' });
    expect(within(impact).getAllByText('—')).toHaveLength(3);
  });

  it('keeps detailed safety values one expansion away', () => {
    show();
    fireEvent.click(screen.getByText('Safety and response details'));
    const table = screen.getByRole('table');
    expect(within(table).getByRole('rowheader', { name: 'Safety result' })).toBeInTheDocument();
    expect(within(table).getByRole('rowheader', { name: 'Delivered relief' })).toBeInTheDocument();
  });

  it('warns when the outcome windows differ', () => {
    const shifted = outcomes.map((item) => item.column === 'proposed'
      ? { ...item, windowEnd: '2026-01-24T19:00:00Z' } : item);
    show(shifted);
    expect(screen.getByRole('alert')).toHaveTextContent('cannot be compared');
    expect(screen.getByText('Comparable dispatch-down energy is unavailable for this case.')).toBeInTheDocument();
  });
});

import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DECISION_COPY } from '../../decision/copy/workspace';
import { fixtureAssessment } from '../../decision/fixture';
import { displayOverall } from '../../decision/rules';
import DecisionSummary from './DecisionSummary';

function renderSummary(stale = false) {
  const overall = displayOverall(fixtureAssessment, stale);
  render(<DecisionSummary assessment={fixtureAssessment} overall={overall} plan={fixtureAssessment.proposed} stale={stale} />);
  return screen.getByRole('region', { name: DECISION_COPY.summaryTitle });
}

describe('decision summary', () => {
  it('names each limiting condition in plain language, then safety, then the plan label', () => {
    const summary = renderSummary();
    expect(within(summary).getByText('A route is overloaded during an existing outage.')).toBeInTheDocument();
    expect(within(summary).getByText('All-island SNSP is at or near its limit.')).toBeInTheDocument();
    const safety = within(summary).getByText(DECISION_COPY.summarySafety);
    const plan = within(summary).getByText(DECISION_COPY.summaryPlan);
    expect(safety.compareDocumentPosition(plan) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // The demonstration proposal is never shown as Actionable.
    expect(within(summary).queryByText('Actionable')).not.toBeInTheDocument();
    expect(summary.textContent).not.toMatch(/\b(T[1-4]|H[1-4])\b/);
  });

  it('leaves the out-of-date notice outside the summary card', () => {
    const summary = renderSummary(true);
    expect(within(summary).queryByText(DECISION_COPY.summaryStale)).not.toBeInTheDocument();
    expect(within(summary).queryByRole('button', { name: DECISION_COPY.rerun })).not.toBeInTheDocument();
  });
});

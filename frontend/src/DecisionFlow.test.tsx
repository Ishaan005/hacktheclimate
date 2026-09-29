import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';
import { FORBIDDEN_PHRASES } from './copy';
import { SEARCH_COPY } from './decision/copy/search';
import { STALE_NOTE } from './decision/copy/shared';
import { DECISION_COPY } from './decision/copy/workspace';

function describeSituation(text: string) {
  fireEvent.change(screen.getByLabelText(SEARCH_COPY.label), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: SEARCH_COPY.find }));
}

async function assessOutageAndSnsp() {
  render(<App />);
  describeSituation('route overloaded during an outage and SNSP near the limit');
  fireEvent.click(screen.getByRole('button', { name: SEARCH_COPY.assess }));
  return screen.findByRole('region', { name: DECISION_COPY.safetyRegion });
}

describe('decision workspace end to end (fixture)', () => {
  it('opens on the decision workspace with no result before an assessment', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1, name: DECISION_COPY.title })).toBeInTheDocument();
    expect(screen.getByText(DECISION_COPY.idleTitle)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: DECISION_COPY.safetyRegion })).not.toBeInTheDocument();
  });

  it('shows several binding conditions, safety first, and never an Actionable demonstration', async () => {
    const safety = await assessOutageAndSnsp();
    const plan = screen.getByRole('region', { name: DECISION_COPY.planRegion });
    // Safety panel comes before the plan in reading order.
    expect(safety.compareDocumentPosition(plan) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(plan).queryByText('Actionable')).not.toBeInTheDocument();
    expect(screen.getAllByText('Historical demonstration').length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Live$/)).not.toBeInTheDocument();
    const text = document.body.textContent?.toLowerCase() ?? '';
    for (const phrase of FORBIDDEN_PHRASES) expect(text).not.toContain(phrase);
    // Internal scenario IDs stay off screen.
    expect(text).not.toMatch(/\b(t[1-4]|h[1-4])\b/);
  });

  it('makes the assessment stale after a fact edit until it is rerun', async () => {
    await assessOutageAndSnsp();
    expect(screen.queryAllByText(STALE_NOTE)).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: /Add Actual flow on limiting route/ }));
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '420' } });
    fireEvent.click(screen.getByRole('button', { name: /Save/ }));
    expect(screen.getAllByText(STALE_NOTE).length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole('button', { name: DECISION_COPY.rerun })[0]);
    await screen.findByRole('region', { name: DECISION_COPY.safetyRegion });
    expect(screen.queryAllByText(STALE_NOTE)).toHaveLength(0);
  });

  it('keeps all-island checks visible in the site view', async () => {
    await assessOutageAndSnsp();
    fireEvent.click(screen.getByRole('radio', { name: 'Precise grid / site' }));
    fireEvent.click(screen.getAllByRole('button', { name: DECISION_COPY.rerun })[0]);
    const safety = await screen.findByRole('region', { name: DECISION_COPY.safetyRegion });
    expect(within(safety).getAllByText(/All-island limits that affect this decision/)[0]).toBeVisible();
  });

  it('keeps a forecast surplus in intake and assesses nothing', () => {
    render(<App />);
    describeSituation('forecast surplus tonight, frequency normal');
    expect(screen.getByText(SEARCH_COPY.causeUnknownHeading)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: SEARCH_COPY.assess })).not.toBeInTheDocument();
  });

  it('offers no control that sends an instruction', async () => {
    await assessOutageAndSnsp();
    for (const button of screen.getAllByRole('button')) {
      expect(button.textContent ?? '').not.toMatch(/\b(send|issue|dispatch)\b/i);
    }
  });

  it('keeps the grid assistant one tab away', () => {
    render(<App />);
    fireEvent.click(screen.getByRole('button', { name: DECISION_COPY.navAssistant }));
    expect(screen.getByLabelText('Describe the situation')).toBeInTheDocument();
  });
});

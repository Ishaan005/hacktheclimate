import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AssistantApp from './AssistantApp';
import * as api from './api';
import { caseSummaryText, reviewSections } from './case';
import { STORAGE_KEY } from './caseStore';
import { REVIEW_COPY, WORKSPACE_COPY } from './copy';
import { detectActionFamily, illustrativeCase } from './fixtures/illustrativeCase';
import { illustrativeScenarios } from './fixtures/illustrativeScenarios';

const [thermal] = illustrativeScenarios;

afterEach(() => vi.restoreAllMocks());

function describeSituation(value: string) {
  fireEvent.change(screen.getByLabelText(WORKSPACE_COPY.situationLabel), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: WORKSPACE_COPY.situationSubmit }));
  return screen.findByRole('region', { name: new RegExp(REVIEW_COPY.title) });
}

function row(review: HTMLElement, label: string): HTMLElement {
  return within(review).getByRole('rowheader', { name: new RegExp(`^${label}`) }).closest('tr') as HTMLElement;
}

describe('fact review', () => {
  it('shows each fact with value, source, time and status before anything is evaluated', async () => {
    const spy = vi.spyOn(api, 'solveSituation');
    render(<AssistantApp />);
    const review = await describeSituation('line overload in the west after the outage');
    const window = row(review, 'Event window');
    expect(window).toHaveTextContent('2026-09-29 15:00–16:30');
    expect(window).toHaveTextContent('Illustrative fixture (invented)');
    expect(within(window).getByText('System inferred')).toBeInTheDocument();
    expect(within(window).getByText(/^Modelled · Illustrative fixture \(invented\) · /)).toBeInTheDocument();
    expect(within(row(review, 'Expected dispatch-down')).getByText('Forecast')).toBeInTheDocument();
    expect(within(review).queryByRole('columnheader', { name: REVIEW_COPY.source })).toBeNull();
    expect(within(review).queryByRole('columnheader', { name: REVIEW_COPY.time })).toBeNull();
    expect(row(review, 'What is limiting renewable output?')).toHaveTextContent('Local network limit, Planned outage makes it worse');
    expect(within(review).getByRole('button', { name: REVIEW_COPY.evaluate })).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });

  it('marks an edited fact as corrected and keeps it after a reload', async () => {
    const { unmount } = render(<AssistantApp />);
    let review = await describeSituation('line overload in the west after the outage');
    fireEvent.click(within(review).getByRole('button', { name: `${REVIEW_COPY.edit} Event window` }));
    fireEvent.change(within(review).getByLabelText('Event window'), { target: { value: '15:00–18:00' } });
    fireEvent.click(within(review).getByRole('button', { name: REVIEW_COPY.save }));
    let window = row(review, 'Event window');
    expect(window).toHaveTextContent('15:00–18:00');
    expect(within(window).getByText('Corrected')).toBeInTheDocument();
    expect(window).toHaveTextContent('Operator correction');

    unmount();
    render(<AssistantApp />);
    review = screen.getByRole('region', { name: new RegExp(REVIEW_COPY.title) });
    window = row(review, 'Event window');
    expect(within(window).getByText('Corrected')).toBeInTheDocument();
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) as string);
    expect(saved.operatorCase.facts.event_window.history).toHaveLength(1);
  });

  it('lists missing facts most-blocking first and allows evaluation once they are added in the table', async () => {
    render(<AssistantApp />);
    const review = await describeSituation('xyzzy plugh');
    const stopped = within(review).getByText(REVIEW_COPY.stoppedTitle).parentElement as HTMLElement;
    const items = within(stopped).getAllByRole('listitem').map((item) => item.textContent);
    expect(items[0]).toBe('What is limiting renewable output?');
    expect(items[1]).toBe('Event window');
    expect(within(review).queryByRole('button', { name: REVIEW_COPY.evaluate })).not.toBeInTheDocument();

    function add(label: string, value: string) {
      fireEvent.click(within(review).getByRole('button', { name: `${REVIEW_COPY.add} ${label}` }));
      fireEvent.change(within(review).getByLabelText(label), { target: { value } });
      fireEvent.click(within(review).getByRole('button', { name: REVIEW_COPY.save }));
    }
    add('What is limiting renewable output?', 'local_network_constraint');
    add('Event window', '14:00–17:00');
    add('Affected area or constraint group', 'West');
    add('Expected dispatch-down', '40');
    add('Material-event probability', '60');
    add('Forecast range', '20–60');

    expect(within(review).queryByText(REVIEW_COPY.stoppedTitle)).not.toBeInTheDocument();
    expect(row(review, 'Expected dispatch-down')).toHaveTextContent('40 MWh');
    expect(within(row(review, 'Affected area')).getByText('Operator supplied')).toBeInTheDocument();
    expect(row(review, 'What is limiting renewable output?')).toHaveTextContent('Local network limit');
    expect(within(review).getByRole('button', { name: REVIEW_COPY.evaluate })).toBeInTheDocument();
  });

  it('rejects a number outside its range', async () => {
    render(<AssistantApp />);
    const review = await describeSituation('xyzzy plugh');
    fireEvent.click(within(review).getByRole('button', { name: `${REVIEW_COPY.add} Material-event probability` }));
    fireEvent.change(within(review).getByLabelText('Material-event probability'), { target: { value: '150' } });
    expect(within(review).getByRole('button', { name: REVIEW_COPY.save })).toBeDisabled();
  });

  it('evaluates the reviewed case and shows the scenario', async () => {
    const spy = vi.spyOn(api, 'solveSituation');
    render(<AssistantApp />);
    const review = await describeSituation('line overload in the west after the outage');
    fireEvent.click(within(review).getByRole('button', { name: REVIEW_COPY.evaluate }));
    await screen.findByRole('region', { name: thermal.title });
    expect(spy).toHaveBeenLastCalledWith(
      expect.objectContaining({ description: 'line overload in the west after the outage', caseSummary: expect.stringContaining('Event window: 2026-09-29 15:00–16:30') }),
      expect.any(AbortSignal),
    );
  });

  it('sends dispatch-down questions straight to the risk view without a review', async () => {
    render(<AssistantApp />);
    fireEvent.change(screen.getByLabelText(WORKSPACE_COPY.situationLabel), { target: { value: 'What is the dispatch-down risk next hour?' } });
    fireEvent.click(screen.getByRole('button', { name: WORKSPACE_COPY.situationSubmit }));
    await screen.findByRole('region', { name: 'Next-hour dispatch-down risk' });
    expect(screen.queryByRole('region', { name: new RegExp(REVIEW_COPY.title) })).not.toBeInTheDocument();
  });
});

describe('illustrative intake', () => {
  const createdAt = '2026-09-29T08:00:00Z';

  it('detects the four core action families', () => {
    expect(detectActionFamily('charge Battery A')).toBe('storage_charging');
    expect(detectActionFamily('move the data centre workload')).toBe('flexible_demand');
    expect(detectActionFamily('reduce Generator B')).toBe('generator_redispatch');
    expect(detectActionFamily('reschedule the outage')).toBe('outage_review');
    expect(detectActionFamily('export on the interconnector')).toBeNull();
  });

  it('treats a comparison without an action as a second situation', () => {
    const operatorCase = illustrativeCase('overload in the west', 'SNSP overnight', createdAt, illustrativeScenarios);
    expect(operatorCase.comparison?.kind).toBe('situation');
    const sections = reviewSections(operatorCase);
    expect(sections.map((section) => section.title)).toEqual(['Situation', 'Comparison: a different situation']);
  });

  it('leaves an unmatched description with an unknown cause and no facts', () => {
    const operatorCase = illustrativeCase('xyzzy', null, createdAt, illustrativeScenarios);
    expect(operatorCase.scenarios).toEqual(['cause_unknown']);
    expect(operatorCase.facts).toEqual({});
  });

  it('writes the reviewed facts and their sources into the case summary', () => {
    const operatorCase = illustrativeCase('overload in the west', null, createdAt, illustrativeScenarios);
    const summary = caseSummaryText(operatorCase);
    expect(summary).toMatch(/^overload in the west\n/);
    expect(summary).toContain('- Expected dispatch-down: 42 MWh (Illustrative fixture (invented))');
  });
});

import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SEARCH_COPY } from '../../decision/copy/search';
import { FAMILY_LABEL, SUGGESTIONS } from '../../decision/scope';
import SituationSearch from './SituationSearch';

function describeSituation(text: string) {
  const input = screen.getByRole('textbox', { name: SEARCH_COPY.label });
  fireEvent.change(input, { target: { value: text } });
  fireEvent.keyDown(input, { key: 'Enter' });
}

function suggestionButtons() {
  const region = screen.getByRole('region', { name: SEARCH_COPY.suggestionsHeading });
  return within(region).getAllByRole('button');
}

function reviewRow(text: string) {
  return screen.getByRole('group', { name: text });
}

describe('situation search', () => {
  it('lists exactly the locked suggestions in plain language, grouped by family', () => {
    const { container } = render(<SituationSearch onAssess={vi.fn()} />);
    expect(suggestionButtons().map((button) => button.textContent)).toEqual(SUGGESTIONS.map((item) => item.text));
    for (const label of Object.values(FAMILY_LABEL)) {
      expect(screen.getByRole('group', { name: label })).toBeInTheDocument();
    }
    // Internal scenario IDs never reach the screen.
    expect(container.textContent).not.toMatch(/\b[TH][1-4]\b/);
  });

  it('shows one review row per matched limit', () => {
    const { container } = render(<SituationSearch onAssess={vi.fn()} />);
    describeSituation('SNSP is near its limit and the upward reserve binds');
    expect(screen.getByRole('heading', { name: SEARCH_COPY.reviewHeading })).toBeInTheDocument();
    const rows = container.querySelectorAll('.review-row');
    expect(rows).toHaveLength(2);
    expect(reviewRow('The upward reserve requirement binds.')).toBeInTheDocument();
    expect(reviewRow('All-island SNSP is at or near its limit.')).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\b[TH][1-4]\b/);
  });

  it('keeps a forecast surplus in intake as cause unknown', () => {
    const onAssess = vi.fn();
    render(<SituationSearch onAssess={onAssess} />);
    describeSituation('Forecast surplus of wind tonight with normal frequency');
    const intake = screen.getByRole('status');
    expect(within(intake).getByText(SEARCH_COPY.causeUnknownHeading)).toBeInTheDocument();
    expect(within(intake).getByText('Measured frequency and time')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: SEARCH_COPY.assess })).toBeNull();
    expect(onAssess).not.toHaveBeenCalled();
    // The operator can still pick a suggestion instead.
    expect(suggestionButtons()).toHaveLength(SUGGESTIONS.length);
  });

  it('asks only to confirm each limit and sends it without typed details', () => {
    const onAssess = vi.fn();
    render(<SituationSearch onAssess={onAssess} />);
    const outage = 'A route is overloaded during an existing outage.';
    const snsp = 'All-island SNSP is at or near its limit.';

    fireEvent.click(screen.getByRole('button', { name: outage }));
    fireEvent.click(screen.getByRole('button', { name: SEARCH_COPY.addAnother }));
    fireEvent.click(screen.getByRole('button', { name: snsp }));
    // Details come from connected feeds, so the review asks for none.
    for (const text of [outage, snsp]) {
      const row = reviewRow(text);
      expect(within(row).queryAllByRole('radio')).toHaveLength(0);
      expect(within(row).queryAllByRole('checkbox')).toHaveLength(0);
      expect(within(row).queryAllByRole('textbox')).toHaveLength(0);
    }
    expect(screen.getByText(SEARCH_COPY.feedNote)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: SEARCH_COPY.assess }));
    expect(onAssess).toHaveBeenCalledTimes(1);
    const [description, conditions] = onAssess.mock.calls[0];
    expect(description).toContain(outage);
    expect(conditions).toEqual([
      {
        scenarioId: 'T3', situationKey: 't_outage_overload', reach: null, limitingAsset: null,
        outageType: null, timeSetting: null, snspDrivers: [], jurisdiction: null, confirmedByOperator: false,
      },
      {
        scenarioId: 'SNSP', situationKey: 'snsp_limit', reach: null, limitingAsset: null,
        outageType: null, timeSetting: null, snspDrivers: [], jurisdiction: null, confirmedByOperator: false,
      },
    ]);
  });

  it('removes a limit on request', () => {
    const onAssess = vi.fn();
    render(<SituationSearch onAssess={onAssess} />);
    const intact = 'A route is overloaded while all equipment is in service.';
    fireEvent.click(screen.getByRole('button', { name: intact }));
    fireEvent.click(within(reviewRow(intact)).getByRole('button', { name: SEARCH_COPY.removeLabel(intact) }));
    expect(screen.queryByRole('button', { name: SEARCH_COPY.assess })).toBeNull();
    expect(onAssess).not.toHaveBeenCalled();
  });

  it('takes the jurisdiction of the minimum units rule from the picked situation', () => {
    const onAssess = vi.fn();
    render(<SituationSearch onAssess={onAssess} />);
    fireEvent.click(screen.getByRole('button', { name: 'The minimum conventional units rule binds in both jurisdictions.' }));
    fireEvent.click(screen.getByRole('button', { name: SEARCH_COPY.assess }));
    expect(onAssess.mock.calls[0][1][0]).toMatchObject({ scenarioId: 'H2', situationKey: 'h_min_units_both', jurisdiction: 'both' });
  });

  it('disables assessment while busy', () => {
    render(<SituationSearch onAssess={vi.fn()} busy />);
    fireEvent.click(screen.getByRole('button', { name: 'All-island SNSP is at or near its limit.' }));
    expect(screen.getByRole('button', { name: SEARCH_COPY.assessing })).toBeDisabled();
  });
});

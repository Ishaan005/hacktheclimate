import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SEARCH_COPY } from '../../decision/copy/search';
import { FAMILY_LABEL, SUGGESTIONS } from '../../decision/scope';
import SituationSearch from './SituationSearch';

function input() {
  return screen.getByRole('textbox', { name: SEARCH_COPY.label });
}

function assessButton() {
  return screen.getByRole('button', { name: SEARCH_COPY.assess });
}

describe('situation search', () => {
  it('enables Assess only once something is typed', () => {
    render(<SituationSearch onAssess={vi.fn()} />);
    expect(assessButton()).toBeDisabled();
    fireEvent.change(input(), { target: { value: '   ' } });
    expect(assessButton()).toBeDisabled();
    fireEvent.change(input(), { target: { value: 'anything at all' } });
    expect(assessButton()).toBeEnabled();
  });

  it('sends the typed text as written, with no review step', () => {
    const onAssess = vi.fn();
    render(<SituationSearch onAssess={onAssess} />);
    const text = 'Wind is backing off near Ballylickey, not sure what binds yet';
    fireEvent.change(input(), { target: { value: `  ${text}  ` } });
    fireEvent.click(assessButton());
    expect(onAssess).toHaveBeenCalledWith(text);
    expect(screen.queryAllByRole('radio')).toHaveLength(0);
    expect(screen.queryByRole('button', { name: /remove/i })).toBeNull();
  });

  it('assesses on Enter and adds a line on Shift+Enter', () => {
    const onAssess = vi.fn();
    render(<SituationSearch onAssess={onAssess} />);
    fireEvent.change(input(), { target: { value: 'SNSP near limit' } });
    fireEvent.keyDown(input(), { key: 'Enter', shiftKey: true });
    expect(onAssess).not.toHaveBeenCalled();
    fireEvent.keyDown(input(), { key: 'Enter' });
    expect(onAssess).toHaveBeenCalledWith('SNSP near limit');
  });

  it('offers only the locked example situations, in plain language, and they fill the box', () => {
    const { container } = render(<SituationSearch onAssess={vi.fn()} />);
    const region = screen.getByRole('region', { name: SEARCH_COPY.suggestionsHeading, hidden: true });
    const buttons = within(region).getAllByRole('button', { hidden: true });
    expect(buttons.map((button) => button.textContent)).toEqual(SUGGESTIONS.map((item) => item.text));
    for (const label of Object.values(FAMILY_LABEL)) {
      expect(within(region).getByRole('group', { name: label, hidden: true })).toBeInTheDocument();
    }
    expect(container.textContent).not.toMatch(/\b[TH][1-4]\b/);
    fireEvent.click(buttons[0]);
    fireEvent.click(buttons[buttons.length - 1]);
    expect(input()).toHaveValue(`${SUGGESTIONS[0].text} ${SUGGESTIONS[SUGGESTIONS.length - 1].text}`);
  });

  it('disables assessment while busy', () => {
    render(<SituationSearch onAssess={vi.fn()} busy />);
    fireEvent.change(input(), { target: { value: 'SNSP near limit' } });
    expect(screen.getByRole('button', { name: SEARCH_COPY.assessing })).toBeDisabled();
  });
});

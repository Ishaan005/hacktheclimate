import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { REVIEW_COPY, WORKSPACE_COPY } from '../copy';
import SituationInput from './SituationInput';

describe('situation input', () => {
  it('submits on Enter and keeps Shift+Enter for a new line', () => {
    const onSubmit = vi.fn();
    render(<SituationInput onSubmit={onSubmit} />);
    const situation = screen.getByLabelText(WORKSPACE_COPY.situationLabel);
    fireEvent.change(situation, { target: { value: 'Line overload in the west\nafter the outage' } });
    fireEvent.keyDown(situation, { key: 'Enter', shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(REVIEW_COPY.comparisonLabel), { target: { value: 'Storage B\ncharging' } });
    fireEvent.keyDown(situation, { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalledWith('Line overload in the west\nafter the outage', 'Storage B\ncharging');
  });

  it('does not submit an empty situation from the keyboard', () => {
    const onSubmit = vi.fn();
    render(<SituationInput onSubmit={onSubmit} />);
    fireEvent.keyDown(screen.getByLabelText(REVIEW_COPY.comparisonLabel), { key: 'Enter' });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

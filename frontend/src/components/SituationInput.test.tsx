import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { WORKSPACE_COPY } from '../copy';
import SituationInput from './SituationInput';

describe('situation input', () => {
  it('submits on Enter and keeps Shift+Enter for a new line', () => {
    const onSubmit = vi.fn();
    render(<SituationInput onSubmit={onSubmit} />);
    const situation = screen.getByLabelText(WORKSPACE_COPY.situationLabel);
    fireEvent.change(situation, { target: { value: 'Line overload in the west\nafter the outage' } });
    fireEvent.keyDown(situation, { key: 'Enter', shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.keyDown(situation, { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalledWith('Line overload in the west\nafter the outage');
  });

  it('does not submit an empty situation from the keyboard', () => {
    const onSubmit = vi.fn();
    render(<SituationInput onSubmit={onSubmit} />);
    fireEvent.keyDown(screen.getByLabelText(WORKSPACE_COPY.situationLabel), { key: 'Enter' });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

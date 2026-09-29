import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Guardrail } from '../types';
import GuardrailStrip from './GuardrailStrip';

function row(name: Guardrail['name'], baseline: Guardrail['baseline'], postAction: Guardrail['postAction']): Guardrail {
  return { name, baseline, postAction, margin: null, timestamp: null, note: null };
}

describe('guardrail strip', () => {
  it('marks a breach on either side with the breach bar and a plain change with the change bar', () => {
    render(
      <GuardrailStrip
        guardrails={[
          row('transmission_line', 'breach', 'within_modelled_limit'),
          row('snsp', 'within_modelled_limit', 'unknown'),
          row('thermal_capacity', 'within_modelled_limit', 'within_modelled_limit'),
        ]}
      />,
    );
    expect(screen.getByRole('rowheader', { name: 'Transmission line' }).closest('tr')).toHaveClass('guardrail-breach');
    expect(screen.getByRole('rowheader', { name: 'SNSP' }).closest('tr')).not.toHaveClass('guardrail-breach');
    expect(screen.getByRole('rowheader', { name: 'SNSP' }).closest('tr')).toHaveClass('guardrail-changed');
    expect(screen.getByRole('rowheader', { name: 'Thermal capacity' }).closest('tr')).not.toHaveAttribute('class');
  });

  it('shows a sentence-case name for a constraint this build does not know', () => {
    render(<GuardrailStrip guardrails={[row('rate_of_change' as Guardrail['name'], 'unknown', 'unknown')]} />);
    expect(screen.getByRole('rowheader', { name: 'Rate of change' })).toBeInTheDocument();
  });
});

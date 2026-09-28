import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DispatchDownChart from './DispatchDownChart';

describe('DispatchDownChart', () => {
  it('draws the day and highlights the selected time', async () => {
    render(<DispatchDownChart target="2026-01-24T01:00" />);
    expect(await screen.findByRole('img', { name: /2026-01-24/ })).toBeInTheDocument();
    expect(screen.getByText('Selected time')).toBeInTheDocument();
    expect(screen.getByText('01:00 UTC')).toBeInTheDocument();
    expect(screen.getByText(/of 48/)).toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DispatchDownCard from './DispatchDownCard';

describe('DispatchDownCard', () => {
  it('shows risk, probability, expected MWh and limits', async () => {
    render(<DispatchDownCard />);
    expect(await screen.findByText('High risk')).toBeInTheDocument();
    expect(screen.getByText('95.4%')).toBeInTheDocument();
    expect(screen.getByText(/37\.2/)).toBeInTheDocument();
    expect(screen.getByText('Historical replay')).toBeInTheDocument();
    expect(screen.getByText(/not a live forecast/)).toBeInTheDocument();
  });

  it('rejects a time outside the replay range', async () => {
    render(<DispatchDownCard />);
    await screen.findByText('High risk');
    fireEvent.change(screen.getByLabelText('Forecast time (UTC)'), { target: { value: '2026-02-05T10:00' } });
    fireEvent.click(screen.getByRole('button', { name: 'Get forecast' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/between 1 Jan 2026/);
  });
});

import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from './api';
import DemoAssistantCard from './components/DemoAssistantCard';

afterEach(() => vi.restoreAllMocks());

it('asks Azure to explain the result and supports a case question', async () => {
  const ask = vi.spyOn(api, 'askWorkspaceCase').mockResolvedValue({ reply: 'The synthetic line clears, but safety evidence is incomplete.', model: 'gpt-4.1' });
  const operatorCase = { id: 'demo-case' };
  render(<DemoAssistantCard operatorCase={operatorCase} />);
  expect(await screen.findByText('The synthetic line clears, but safety evidence is incomplete.')).toBeInTheDocument();
  expect(ask).toHaveBeenCalledWith(operatorCase, expect.stringContaining('Explain this modeled result'), [], expect.any(AbortSignal));

  fireEvent.change(screen.getByLabelText('Ask about this result'), { target: { value: 'Why is it conditional?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
  expect(await screen.findByText('Why is it conditional?')).toBeInTheDocument();
  expect(ask).toHaveBeenLastCalledWith(operatorCase, 'Why is it conditional?', expect.arrayContaining([
    expect.objectContaining({ question: expect.stringContaining('Explain this modeled result') }),
  ]), expect.any(AbortSignal));
});

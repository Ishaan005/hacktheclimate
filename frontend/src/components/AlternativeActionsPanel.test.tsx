import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { WORKSPACE_COPY } from '../copy';
import { illustrativeScenarios } from '../fixtures/illustrativeScenarios';
import ScenarioWorkspace from './ScenarioWorkspace';

function scenario(id: string) {
  const found = illustrativeScenarios.find((item) => item.id === id);
  if (!found) throw new Error(`No scenario ${id}`);
  return found;
}

describe('alternative actions', () => {
  it('ranks alternatives below the recommendation and links to them', () => {
    render(<ScenarioWorkspace scenario={scenario('illustrative-thermal-west')} />);
    const card = screen.getByRole('region', { name: new RegExp(WORKSPACE_COPY.actionTitle) });
    expect(within(card).getByRole('link', { name: WORKSPACE_COPY.actionRank(3) })).toHaveAttribute('href', '#alternative-actions');
    expect(within(card).getByRole('list', { name: WORKSPACE_COPY.actionWhyTitle })).toHaveTextContent('Avoids the most dispatch-down waste');
    const panel = screen.getByRole('region', { name: new RegExp(WORKSPACE_COPY.alternativesTitle) });
    const rows = within(panel).getAllByRole('row').slice(1) as HTMLTableRowElement[];
    expect(rows.map((row) => row.cells[0].textContent)).toEqual(['#2', '#3']);
    expect(rows[1]).toHaveTextContent('Coordination with the field crew not confirmed');
    expect(within(rows[1]).getByText('Conditional')).toBeInTheDocument();
  });

  it('lists rejected actions from rank 1 when nothing is recommended', () => {
    render(<ScenarioWorkspace scenario={scenario('illustrative-snsp-night')} />);
    expect(screen.getByRole('link', { name: WORKSPACE_COPY.actionNoneConsidered(1) })).toBeInTheDocument();
    const panel = screen.getByRole('region', { name: new RegExp(WORKSPACE_COPY.alternativesRejectedTitle) });
    expect((within(panel).getAllByRole('row')[1] as HTMLTableRowElement).cells[0]).toHaveTextContent('#1');
  });

  it('renders no panel when there are no alternatives', () => {
    render(<ScenarioWorkspace scenario={scenario('illustrative-inertia-south')} />);
    expect(screen.queryByRole('region', { name: new RegExp(WORKSPACE_COPY.alternativesRejectedTitle) })).toBeNull();
    expect(screen.queryByRole('link', { name: /considered/ })).toBeNull();
  });
});

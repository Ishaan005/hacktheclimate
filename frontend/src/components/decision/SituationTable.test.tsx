import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STALE_NOTE } from '../../decision/copy/shared';
import { SITUATION_COPY } from '../../decision/copy/situation';
import { fixtureAssessment } from '../../decision/fixture';
import type { OperatorEdit } from '../../decision/types';
import SituationTable from './SituationTable';

const { facts, conditions, activeInstructions } = fixtureAssessment;
const transmissionOnly = conditions.filter((condition) => condition.scenarioId === 'T3');

function renderTable(overrides: Partial<Parameters<typeof SituationTable>[0]> = {}) {
  const props = {
    facts,
    conditions,
    activeInstructions,
    edits: [] as OperatorEdit[],
    stale: false,
    onEdit: vi.fn(),
    onRerun: vi.fn(),
    ...overrides,
  };
  render(<SituationTable {...props} />);
  return props;
}

function rowFor(label: string): HTMLElement {
  const row = screen.getByRole('rowheader', { name: label }).closest('tr');
  if (!row) throw new Error(`No row for ${label}`);
  return row;
}

describe('situation table', () => {
  it('shows only the families of the binding conditions', () => {
    renderTable({ conditions: transmissionOnly });
    expect(screen.getByRole('heading', { name: 'Transmission' })).toBeInTheDocument();
    expect(screen.getByText('Studied flow on limiting route')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'SNSP' })).not.toBeInTheDocument();
    expect(screen.queryByText('Wind output')).not.toBeInTheDocument();
  });

  it('omits a missing value rather than showing an empty field', () => {
    renderTable({ facts: facts.map((fact) => fact.id === 'actual_flow'
      ? { ...fact, missingReason: 'No decision-time operational measurement supplied' } : fact) });
    expect(screen.queryByRole('rowheader', { name: 'Actual flow on limiting route' })).not.toBeInTheDocument();
    expect(screen.queryByText('No decision-time operational measurement supplied')).not.toBeInTheDocument();
    expect(within(rowFor('Solar output')).getByText('0 MW')).toBeInTheDocument();
  });

  it('marks a planning value as modeled with its synthetic source', () => {
    renderTable({ facts: facts.map((fact) => fact.id === 'actual_flow'
      ? { ...fact, value: 60, source: 'Synthetic planning case (not live)',
        origin: 'planning' as const, state: 'modeled' as const } : fact) });
    const row = rowFor('Actual flow on limiting route');
    expect(within(row).getByText('Modeled')).toBeInTheDocument();
    expect(within(row).getByText('Synthetic planning model')).toBeInTheDocument();
    expect(within(row).getByText('Synthetic planning case (not live)', { exact: false })).toBeInTheDocument();
  });

  it('does not ask for a reliable, current feed value', () => {
    renderTable();
    expect(within(rowFor('Wind output')).queryByRole('button')).not.toBeInTheDocument();
    expect(within(rowFor('Outage equipment')).queryByRole('button')).not.toBeInTheDocument();
  });

  it('saves an edited number as a number', () => {
    const { onEdit } = renderTable();
    fireEvent.click(screen.getByRole('button', { name: 'Edit Studied flow on limiting route' }));
    fireEvent.change(screen.getByLabelText('Studied flow on limiting route'), { target: { value: '450' } });
    fireEvent.click(screen.getByRole('button', { name: SITUATION_COPY.save }));
    expect(onEdit).toHaveBeenCalledWith('studied_flow', 450);
  });

  it('shows the note on a conflicting row', () => {
    renderTable();
    const row = rowFor('Net interconnector transfer (+import)');
    expect(within(row).getByText('Conflicting')).toBeInTheDocument();
    expect(within(row).getByText('Interconnector schedule shows +250 MW.')).toBeInTheDocument();
  });

  it('lists the instructions already in force', () => {
    renderTable();
    expect(screen.getByRole('heading', { name: SITUATION_COPY.instructionsTitle })).toBeInTheDocument();
    expect(screen.getByText('Wind group WDT limit 180 MW')).toBeInTheDocument();
    expect(screen.getByText('North-west wind group')).toBeInTheDocument();
  });

  it('omits an empty instruction section', () => {
    renderTable({ activeInstructions: [] });
    expect(screen.queryByRole('heading', { name: SITUATION_COPY.instructionsTitle })).not.toBeInTheDocument();
  });

  it('marks edited rows and logs the edit', () => {
    const edited = facts.map((fact) => (fact.id === 'actual_flow'
      ? { ...fact, value: 440, origin: 'operator' as const, state: 'current' as const, source: 'Operator' }
      : fact));
    renderTable({ facts: edited, edits: [{ factId: 'actual_flow', label: 'Actual flow on limiting route', from: null, to: 440, at: '2026-01-24T15:45:00Z' }] });
    expect(within(rowFor('Actual flow on limiting route')).getByText('Edited (was Missing)')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: SITUATION_COPY.editsTitle })).toBeInTheDocument();
    expect(screen.getByText('Missing → 440 MW')).toBeInTheDocument();
  });

  it('offers a rerun when the assessment is out of date', () => {
    const { onRerun } = renderTable({ stale: true });
    expect(screen.getByText(STALE_NOTE)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: SITUATION_COPY.rerun }));
    expect(onRerun).toHaveBeenCalledTimes(1);
  });

  it('hides the rerun notice when current', () => {
    renderTable();
    expect(screen.queryByRole('button', { name: SITUATION_COPY.rerun })).not.toBeInTheDocument();
  });
});

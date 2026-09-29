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
    onEdit: vi.fn(),
    ...overrides,
  };
  render(<SituationTable {...props} />);
  return props;
}

// Rows behind the closed disclosure are still in the DOM.
function rowFor(label: string): HTMLElement {
  const row = screen.getByRole('rowheader', { name: label, hidden: true }).closest('tr');
  if (!row) throw new Error(`No row for ${label}`);
  return row;
}

function missingDisclosure(): HTMLDetailsElement {
  const details = document.querySelector('details.disclosure');
  if (!(details instanceof HTMLDetailsElement)) throw new Error('No missing-facts disclosure');
  return details;
}

describe('situation table', () => {
  it('titles the section and summarises the fact states', () => {
    renderTable();
    expect(screen.getByRole('heading', { level: 2, name: SITUATION_COPY.title })).toBeInTheDocument();
    expect(screen.getByText('7 current · 1 stale · 1 conflicting · 2 missing')).toBeInTheDocument();
  });

  it('leaves states that do not occur out of the summary', () => {
    renderTable({ conditions: transmissionOnly });
    expect(screen.getByText('3 current · 1 stale · 1 missing')).toBeInTheDocument();
  });

  it('keeps missing facts in a closed disclosure with the count', () => {
    renderTable();
    const details = missingDisclosure();
    expect(details.open).toBe(false);
    expect(within(details).getByText('Show 2 missing facts')).toBeInTheDocument();
    expect(details).toContainElement(rowFor('Actual flow on limiting route'));
    expect(details).toContainElement(rowFor('Inertia and RoCoF study'));
    expect(details).not.toContainElement(rowFor('Wind output'));
  });

  it('keeps stale and conflicting facts visible without opening the disclosure', () => {
    renderTable();
    const details = missingDisclosure();
    expect(details).not.toContainElement(rowFor('Route rating (winter)'));
    expect(details).not.toContainElement(rowFor('Net interconnector transfer (+import)'));
    expect(screen.getByRole('rowheader', { name: 'Route rating (winter)' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'Net interconnector transfer (+import)' })).toBeInTheDocument();
  });

  it('says so when feeds supplied nothing, and still offers the missing facts', () => {
    const allMissing = facts.map((fact) => ({ ...fact, value: null, origin: null, state: 'missing' as const, source: null, timestamp: null }));
    renderTable({ facts: allMissing });
    expect(screen.getByText(SITUATION_COPY.noSupplied)).toBeInTheDocument();
    expect(within(missingDisclosure()).getByText(`Show ${facts.length} missing facts`)).toBeInTheDocument();
    expect(within(rowFor('Wind output')).getByRole('button', { name: 'Add Wind output', hidden: true })).toBeInTheDocument();
  });

  it('shows no origin for a fact nothing supplied', () => {
    const unsupplied = facts.map((fact) => (fact.id === 'actual_flow' ? { ...fact, origin: null } : fact));
    renderTable({ facts: unsupplied });
    const row = rowFor('Actual flow on limiting route');
    expect(within(row).queryByText('Inferred')).not.toBeInTheDocument();
    expect(within(row).queryByText('Measured')).not.toBeInTheDocument();
  });

  it('says Missing once in the value and once in the state', () => {
    renderTable();
    const row = rowFor('Actual flow on limiting route');
    expect(within(row).getAllByText(SITUATION_COPY.missing)).toHaveLength(2);
    expect(within(row).getByText(SITUATION_COPY.missing, { selector: '.chip' })).toHaveClass('chip-unknown');
    expect(within(row).getByText(SITUATION_COPY.missing, { selector: '.situation-value' })).not.toHaveClass('mono');
  });

  it('shows only the families of the binding conditions', () => {
    renderTable({ conditions: transmissionOnly });
    expect(screen.getAllByRole('heading', { name: 'Transmission' }).length).toBeGreaterThan(0);
    expect(screen.getByText('Studied flow on limiting route')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'SNSP' })).not.toBeInTheDocument();
    expect(screen.queryByText('Wind output')).not.toBeInTheDocument();
  });

  it('shows a missing value as Missing, never zero', () => {
    renderTable();
    const row = rowFor('Actual flow on limiting route');
    expect(within(row).getAllByText(SITUATION_COPY.missing).length).toBeGreaterThan(0);
    expect(within(row).queryByText(/^0/)).not.toBeInTheDocument();
    expect(within(row).getByRole('button', { name: 'Add Actual flow on limiting route', hidden: true })).toBeInTheDocument();
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

  it('says when no instructions are recorded, in one line', () => {
    renderTable({ activeInstructions: [] });
    expect(screen.getByText(SITUATION_COPY.noInstructions)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: SITUATION_COPY.instructionsTitle })).not.toBeInTheDocument();
  });

  it('marks edited rows and logs the edit', () => {
    const edited = facts.map((fact) => (fact.id === 'actual_flow'
      ? { ...fact, value: 440, origin: 'operator' as const, state: 'current' as const, source: 'Operator' }
      : fact));
    renderTable({ facts: edited, edits: [{ factId: 'actual_flow', label: 'Actual flow on limiting route', from: null, to: 440, at: '2026-01-24T15:45:00Z' }] });
    const row = rowFor('Actual flow on limiting route');
    expect(within(row).getByText('Edited (was Missing)')).toBeInTheDocument();
    // An operator-added value leaves the missing disclosure.
    expect(missingDisclosure()).not.toContainElement(row);
    expect(screen.getByRole('heading', { name: SITUATION_COPY.editsTitle })).toBeInTheDocument();
    expect(screen.getByText('Missing → 440 MW')).toBeInTheDocument();
  });

  it('has no out-of-date notice of its own', () => {
    renderTable();
    expect(screen.queryByText(STALE_NOTE)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /rerun/i })).not.toBeInTheDocument();
  });
});

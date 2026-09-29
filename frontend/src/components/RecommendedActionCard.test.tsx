import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ACTION_FAMILY_LABEL, COPY, FORBIDDEN_PHRASES, WORKSPACE_COPY } from '../copy';
import { illustrativeScenarios } from '../fixtures/illustrativeScenarios';
import { resolveSituation } from '../scenarios';
import type { RecommendedAction } from '../types';
import RecommendedActionCard from './RecommendedActionCard';

function actionFor(family: RecommendedAction['family']): RecommendedAction {
  const action = illustrativeScenarios.find((scenario) => scenario.action?.family === family)?.action;
  if (!action) throw new Error(`No illustrative ${family} action`);
  return action;
}

function renderCard(action: RecommendedAction) {
  render(<RecommendedActionCard action={action} noActionReason={null} />);
  return screen.getByRole('region', { name: new RegExp(WORKSPACE_COPY.actionTitle) });
}

function field(card: HTMLElement, label: string): string {
  return within(card).getByText(label).nextElementSibling?.textContent ?? '';
}

describe('action-family detail modules', () => {
  it('has an illustrative scenario for every action family', () => {
    for (const family of Object.keys(ACTION_FAMILY_LABEL) as RecommendedAction['family'][]) {
      expect(actionFor(family).family).toBe(family);
    }
  });

  it('switches action detail slides from the dropdown', () => {
    const card = renderCard(actionFor('generator_redispatch'));
    // Hidden slides have no accessible name, so find them by their label.
    const slide = (name: string) => card.querySelector(`[aria-roledescription="slide"][aria-label="${name}"]`);
    const select = within(card).getByRole('combobox', { name: WORKSPACE_COPY.actionDetailsSummary });
    expect(slide('1 of 4: Overview')).toBeVisible();
    expect(slide('3 of 4: Generator redispatch')).not.toBeVisible();
    fireEvent.change(select, { target: { value: '1' } });
    expect(slide('2 of 4: Schedule')).toBeVisible();
    fireEvent.change(select, { target: { value: '3' } });
    expect(slide(`4 of 4: ${WORKSPACE_COPY.actionCostsTitle}`)).toBeVisible();
    expect(slide('1 of 4: Overview')).not.toBeVisible();
  });

  it('keeps the conditional warning outside the carousel', () => {
    const card = renderCard(actionFor('outage_review'));
    expect(within(card).getByText(WORKSPACE_COPY.actionConditional).closest('.action-carousel')).toBeNull();
  });

  it('renders generator redispatch detail and its cost', () => {
    const card = renderCard(actionFor('generator_redispatch'));
    expect(field(card, 'Ramp rate')).toBe('4.0 MW/min');
    expect(field(card, 'Minimum stable generation')).toBe('40 MW');
    expect(field(card, 'Start and stop restrictions')).toMatch(/no commitment change/);
    expect(field(card, 'Services lost')).toBe('Upward reserve above 20 MW');
    expect(field(card, 'Estimated redispatch cost')).toBe('€1,250');
  });

  it('renders storage limits, efficiency and rebound', () => {
    const card = renderCard(actionFor('storage_charging'));
    expect(field(card, 'State of charge limits')).toBe('10%–90%');
    expect(field(card, 'Round-trip efficiency')).toBe('85%');
    expect(field(card, 'Rebound requirement')).toMatch(/Discharge 20 MW/);
  });

  it('renders flexible demand direction, relief per MW and costs', () => {
    const card = renderCard(actionFor('flexible_demand'));
    expect(field(card, 'Direction')).toBe('Increase');
    expect(field(card, 'Demand change')).toBe('25 MW');
    expect(field(card, 'Constraint relief per MW')).toBe('0.58 MW/MW');
    expect(field(card, 'Rebound-energy cost')).toBe(COPY.notAvailable);
  });

  it('asks for an outage review, never a cancellation, and marks it conditional', () => {
    const card = renderCard(actionFor('outage_review'));
    expect(within(card).getByText(/^Review by 09:00 — Line M-1 outage: move the outage/)).toBeInTheDocument();
    expect(within(card).getByText('Conditional', { selector: '.chip' })).toBeInTheDocument();
    expect(within(card).getByText(WORKSPACE_COPY.actionConditional)).toBeInTheDocument();
    expect(field(card, 'Outage ID')).toBe('OUT-0001');
    expect(field(card, 'Alternative window')).toBe('18:00–22:00');
    expect(card.textContent?.toLowerCase()).not.toContain('cancel');
  });

  it('shows an executable action without the conditional warning', () => {
    const card = renderCard(actionFor('storage_charging'));
    expect(within(card).getByText('Executable')).toBeInTheDocument();
    expect(within(card).queryByText(WORKSPACE_COPY.actionConditional)).not.toBeInTheDocument();
  });

  it('shows missing detail as not available, never as zero', () => {
    const action = actionFor('generator_redispatch');
    if (action.family !== 'generator_redispatch') throw new Error('unexpected family');
    const card = renderCard({
      ...action,
      details: { ...action.details, rampRateMwPerMin: null, servicesLost: null, redispatchCostEur: null },
    });
    expect(field(card, 'Ramp rate')).toBe(COPY.notAvailable);
    expect(field(card, 'Services lost')).toBe(COPY.notAvailable);
    expect(field(card, 'Estimated redispatch cost')).toBe(COPY.notAvailable);
  });

  it('uses no overclaiming copy in any family', () => {
    for (const scenario of illustrativeScenarios) {
      if (!scenario.action) continue;
      const { unmount } = render(<RecommendedActionCard action={scenario.action} noActionReason={null} />);
      const text = document.body.textContent?.toLowerCase() ?? '';
      for (const phrase of FORBIDDEN_PHRASES) expect(text).not.toContain(phrase);
      unmount();
    }
  });

  it('matches each scenario from a plain description', () => {
    expect(resolveSituation('south-east solar export limit, move data centre workload', illustrativeScenarios)?.action?.family).toBe('flexible_demand');
    expect(resolveSituation('planned outage in the midlands during high wind', illustrativeScenarios)?.action?.family).toBe('outage_review');
    expect(resolveSituation('low inertia at midday in the south', illustrativeScenarios)?.action).toBeNull();
  });
});

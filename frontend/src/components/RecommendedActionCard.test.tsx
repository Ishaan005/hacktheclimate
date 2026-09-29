import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ACTION_FAMILY_LABEL, FORBIDDEN_PHRASES, WORKSPACE_COPY } from '../copy';
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

describe('recommended action card', () => {
  it('has an illustrative scenario for every action family', () => {
    for (const family of Object.keys(ACTION_FAMILY_LABEL) as RecommendedAction['family'][]) {
      expect(actionFor(family).family).toBe(family);
    }
  });

  it('shows the overview and keeps the ordered steps in a closed dropdown', () => {
    const card = renderCard(actionFor('generator_redispatch'));
    expect(within(card).getByText('60 MW')).toBeInTheDocument();
    const summary = within(card).getByText(`${WORKSPACE_COPY.actionStepsTitle} (4)`);
    const details = summary.closest('details') as HTMLDetailsElement;
    expect(details).not.toHaveAttribute('open');
    fireEvent.click(summary);
    const steps = within(details).getAllByRole('listitem');
    expect(steps[0]).toHaveTextContent('14:55Issue a dispatch instruction to Generator A');
    expect(steps[3]).toHaveTextContent('16:30Release the instruction');
  });

  it('closes the steps dropdown on Escape and on a click outside', () => {
    const card = renderCard(actionFor('generator_redispatch'));
    const details = within(card).getByText(`${WORKSPACE_COPY.actionStepsTitle} (4)`).closest('details') as HTMLDetailsElement;
    details.open = true;
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(details.open).toBe(false);
    details.open = true;
    fireEvent.mouseDown(within(details).getAllByRole('listitem')[0]);
    expect(details.open).toBe(true);
    fireEvent.mouseDown(document.body);
    expect(details.open).toBe(false);
  });

  it('shows no family detail fields or costs', () => {
    const card = renderCard(actionFor('generator_redispatch'));
    expect(within(card).queryByText('Ramp rate')).toBeNull();
    expect(within(card).queryByText('Estimated redispatch cost')).toBeNull();
  });

  it('marks a step with no fixed time', () => {
    const card = renderCard(actionFor('outage_review'));
    expect(within(card).getAllByRole('listitem', { hidden: true })[1]).toHaveTextContent(/^—Confirm the field crew/);
  });

  it('asks for an outage review, never a cancellation, and marks it conditional', () => {
    const card = renderCard(actionFor('outage_review'));
    expect(within(card).getByText(/^Review by 09:00 — Line M-1 outage: move the outage/)).toBeInTheDocument();
    expect(within(card).getByText('Conditional', { selector: '.chip' })).toBeInTheDocument();
    expect(within(card).getByText(WORKSPACE_COPY.actionConditional)).toBeInTheDocument();
    expect(card.textContent?.toLowerCase()).not.toContain('cancel');
  });

  it('shows an executable action without the conditional warning', () => {
    const card = renderCard(actionFor('storage_charging'));
    expect(within(card).getByText('Executable')).toBeInTheDocument();
    expect(within(card).queryByText(WORKSPACE_COPY.actionConditional)).not.toBeInTheDocument();
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

import { render, screen, within } from '@testing-library/react';
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

  it('keeps family detail behind a disclosure labelled with the family', () => {
    const card = renderCard(actionFor('generator_setpoint'));
    const summary = within(card).getByText(`${WORKSPACE_COPY.actionDetailsSummary}: Generator active-power output`);
    expect(summary.closest('details')).not.toHaveAttribute('open');
  });

  it('renders generator setpoint detail and its redispatch cost', () => {
    const card = renderCard(actionFor('generator_setpoint'));
    expect(field(card, 'Ramp rate')).toBe('4.0 MW/min');
    expect(field(card, 'Minimum stable generation')).toBe('40 MW');
    expect(field(card, 'Services lost')).toBe('Upward reserve above 20 MW');
    expect(field(card, 'Estimated redispatch cost')).toBe('€1,250');
  });

  it('renders commitment timing for a start', () => {
    const card = renderCard(actionFor('commitment_change'));
    expect(field(card, 'Target commitment')).toBe('Online');
    expect(field(card, 'Hot, warm or cold')).toBe('Warm');
    expect(field(card, 'Synchronisation time')).toBe('50 min');
    expect(within(card).queryByText('Shutdown time')).not.toBeInTheDocument();
    expect(field(card, 'Minimum-run cost')).toBe('€5,600');
  });

  it('renders storage limits, efficiency and rebound', () => {
    const card = renderCard(actionFor('storage_charging'));
    expect(field(card, 'State of charge limits')).toBe('10%–90%');
    expect(field(card, 'Round-trip efficiency')).toBe('85%');
    expect(field(card, 'Rebound requirement')).toMatch(/Discharge 20 MW/);
  });

  it('renders signed reactive power and tap change', () => {
    const card = renderCard(actionFor('reactive_control'));
    expect(field(card, 'Target reactive power')).toBe('−40 Mvar');
    expect(field(card, 'Tap position')).toBe('9 to 7');
    expect(field(card, 'Reactive capability at present output')).toBe('−60 Mvar to 0 Mvar at 0 MW');
  });

  it('renders renewable limit window from the action times', () => {
    const card = renderCard(actionFor('renewable_limit'));
    expect(field(card, 'Total reduction')).toBe('25 MW');
    expect(field(card, 'Limit start')).toBe('12:00');
    expect(field(card, 'Limit end')).toBe('14:00');
    expect(field(card, 'Affected units')).toBe('Solar Farm E, Solar Farm F, Wind Farm G');
  });

  it('never shows an unconfirmed interconnector request as executable', () => {
    const action = actionFor('interconnector_request');
    // Even if the solver marks it executable, coordination status wins.
    const card = renderCard({ ...action, executability: 'executable' });
    expect(within(card).getByText('Unconfirmed', { selector: '.chip' })).toBeInTheDocument();
    expect(within(card).queryByText('Executable')).not.toBeInTheDocument();
    expect(within(card).getByText(WORKSPACE_COPY.interconnectorNotConfirmed)).toBeInTheDocument();
    expect(within(card).getByText(/^Requested 19:00 — Interconnector C/)).toBeInTheDocument();
    expect(field(card, 'Counterparty coordination')).toBe('Unconfirmed');
  });

  it('treats a confirmed interconnector request as the solver reported', () => {
    const action = actionFor('interconnector_request');
    if (action.family !== 'interconnector_request') throw new Error('unexpected family');
    const card = renderCard({ ...action, details: { ...action.details, coordinationStatus: 'confirmed' } });
    expect(within(card).getByText('Conditional')).toBeInTheDocument();
    expect(within(card).queryByText(WORKSPACE_COPY.interconnectorNotConfirmed)).not.toBeInTheDocument();
  });

  it('shows missing detail as not available, never as zero', () => {
    const action = actionFor('generator_setpoint');
    if (action.family !== 'generator_setpoint') throw new Error('unexpected family');
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

  it('matches each new scenario from a plain description', () => {
    expect(resolveSituation('low inertia at midday in the south', illustrativeScenarios)?.action?.family).toBe('commitment_change');
    expect(resolveSituation('high voltage in Dublin at light load', illustrativeScenarios)?.action?.family).toBe('reactive_control');
    expect(resolveSituation('south-east solar export limit', illustrativeScenarios)?.action?.family).toBe('renewable_limit');
    expect(resolveSituation('wind surplus, export on the interconnector', illustrativeScenarios)?.action?.family).toBe('interconnector_request');
  });
});

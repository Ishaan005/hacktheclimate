import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';
import OutcomeComparisonPanel from './components/OutcomeComparisonPanel';
import { FORBIDDEN_PHRASES, REVIEW_COPY, WORKSPACE_COPY } from './copy';
import { illustrativeScenarios } from './fixtures/illustrativeScenarios';
import { DEFAULT_TARGET } from './dispatchDown';
import { dispatchDownReductionPct, resolveFixtureSolver, resolveSituation } from './scenarios';

const [thermal, voltage, snsp] = illustrativeScenarios;

function request(description: string) {
  return { description, threadId: null, answers: [] };
}

function expectNoForbiddenCopy() {
  const text = document.body.textContent?.toLowerCase() ?? '';
  for (const phrase of FORBIDDEN_PHRASES) expect(text).not.toContain(phrase);
}

function submitSituation(value: string) {
  fireEvent.change(screen.getByLabelText(WORKSPACE_COPY.situationLabel), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: WORKSPACE_COPY.situationSubmit }));
}

// Describe, then evaluate from the fact review. Matched illustrative
// descriptions come back with every required fact filled.
async function evaluateSituation(value: string) {
  submitSituation(value);
  fireEvent.click(await screen.findByRole('button', { name: REVIEW_COPY.evaluate }));
}

describe('situation input and workspace', () => {
  it('starts with only the input field and no scenario', () => {
    render(<App />);
    expect(screen.getByLabelText(WORKSPACE_COPY.situationLabel)).toBeInTheDocument();
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: WORKSPACE_COPY.situationSubmit })).toBeDisabled();
  });

  it('returns a complete instruction with security before value', async () => {
    render(<App />);
    await evaluateSituation('line overload in the west after the outage');
    const region = await screen.findByRole('region', { name: thermal.title });
    expect(within(region).getByText('Issued 14:55 — Generator A to 100 MW by 15:10, effective until 16:30.')).toBeInTheDocument();
    expect(within(region).getByText(WORKSPACE_COPY.illustrativeNote)).toBeInTheDocument();
    expect(within(region).getByText('Advisory')).toBeInTheDocument();

    const text = (region.textContent ?? '').toLowerCase();
    const security = text.indexOf('security result');
    expect(security).toBeGreaterThanOrEqual(0);
    expect(security).toBeLessThan(text.indexOf('net financial value'));
    expect(within(region).getByText('30 MWh')).toBeInTheDocument();
    expect(within(region).getByText('71%')).toBeInTheDocument();
    expectNoForbiddenCopy();
  });

  it('replaces the result with a new description', async () => {
    render(<App />);
    await evaluateSituation('overload in the west');
    await screen.findByRole('region', { name: thermal.title });
    await evaluateSituation('Low voltage in the north-west at the evening ramp');
    const region = await screen.findByRole('region', { name: voltage.title });
    expect(within(region).getByText(/Storage B to charging at 20 MW/)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: thermal.title })).not.toBeInTheDocument();
  });

  it('shows no action when the scenario has none', async () => {
    render(<App />);
    await evaluateSituation('SNSP overnight');
    const region = await screen.findByRole('region', { name: snsp.title });
    expect(within(region).getByText(WORKSPACE_COPY.actionNone)).toBeInTheDocument();
    expect(within(region).getByText(snsp.noActionReason as string)).toBeInTheDocument();
  });

  it('returns the next-hour dispatch-down risk and its day chart', async () => {
    render(<App />);
    submitSituation('What is the dispatch-down risk next hour?');
    const card = await screen.findByRole('region', { name: 'Next-hour dispatch-down risk' });
    expect(await within(card).findByText('High risk')).toBeInTheDocument();
    expect(within(card).getByText('95.4%')).toBeInTheDocument();
    expect(await screen.findByRole('region', { name: /Dispatch-down risk through/ })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: thermal.title })).not.toBeInTheDocument();
  });

  it('asks for every required fact when nothing matches, and evaluates nothing', async () => {
    render(<App />);
    submitSituation('xyzzy plugh');
    const review = await screen.findByRole('region', { name: new RegExp(REVIEW_COPY.title) });
    expect(within(review).getByText(REVIEW_COPY.stoppedTitle)).toBeInTheDocument();
    expect(within(review).queryByRole('button', { name: REVIEW_COPY.evaluate })).not.toBeInTheDocument();
    expect(within(review).getByRole('button', { name: `${REVIEW_COPY.add} Event window` })).toBeInTheDocument();
  });

  it('shows N/A reduction when baseline waste is zero and never shows unknown as within limit', () => {
    render(<OutcomeComparisonPanel scenario={voltage} />);
    expect(dispatchDownReductionPct(voltage)).toBe('n/a');
    expect(screen.getByText('N/A')).toBeInTheDocument();
    expect(screen.getByText(`${WORKSPACE_COPY.postAction} security result:`).parentElement).toHaveTextContent('Unknown');
  });
});

describe('situation matcher', () => {
  it('matches on area, asset and limit words and ignores empty input', () => {
    expect(resolveSituation('overload on the west line', illustrativeScenarios)?.id).toBe(thermal.id);
    expect(resolveSituation('SNSP overnight', illustrativeScenarios)?.id).toBe(snsp.id);
    expect(resolveSituation('   ', illustrativeScenarios)).toBeNull();
    expect(resolveSituation('the and for', illustrativeScenarios)).toBeNull();
  });

  it('routes dispatch-down questions to the replay view at a valid named time', () => {
    expect(resolveFixtureSolver(request('dispatch-down risk at 2026-01-20 14:30'), illustrativeScenarios))
      .toEqual({ kind: 'dispatch_down_risk', target: '2026-01-20T14:30' });
    // Outside the January replay: fall back to the default time.
    expect(resolveFixtureSolver(request('dispatch down 2026-03-01 10:00'), illustrativeScenarios))
      .toEqual({ kind: 'dispatch_down_risk', target: DEFAULT_TARGET });
    expect(resolveFixtureSolver(request('overload in the west'), illustrativeScenarios)?.kind).toBe('scenario');
    for (const phrase of ['DD next hour', 'show the graph', 'dispatch down', 'risk?', 'Dispatchdown forecast']) {
      expect(resolveFixtureSolver(request(phrase), illustrativeScenarios)?.kind).toBe('dispatch_down_risk');
    }
  });
});

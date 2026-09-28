import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';
import OutcomeComparisonPanel from './components/OutcomeComparisonPanel';
import { FORBIDDEN_PHRASES, WORKSPACE_COPY } from './copy';
import { illustrativeScenarios } from './fixtures/illustrativeScenarios';
import { dispatchDownReductionPct, resolveSituation } from './scenarios';

const [thermal, voltage, snsp] = illustrativeScenarios;

function expectNoForbiddenCopy() {
  const text = document.body.textContent?.toLowerCase() ?? '';
  for (const phrase of FORBIDDEN_PHRASES) expect(text).not.toContain(phrase);
}

function submitSituation(value: string) {
  fireEvent.change(screen.getByLabelText(WORKSPACE_COPY.situationLabel), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: WORKSPACE_COPY.situationSubmit }));
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
    submitSituation('line overload in the west after the outage');
    const region = await screen.findByRole('region', { name: thermal.title });
    expect(within(region).getByText('Issued 14:55 — Generator A to 100 MW by 15:10, effective until 16:30.')).toBeInTheDocument();
    expect(within(region).getByText(WORKSPACE_COPY.illustrativeNote)).toBeInTheDocument();
    expect(within(region).getByText('Advisory')).toBeInTheDocument();

    const text = region.textContent ?? '';
    expect(text.indexOf('Security result')).toBeLessThan(text.indexOf('Net financial value'));
    expect(within(region).getByText('30 MWh')).toBeInTheDocument();
    expect(within(region).getByText('71%')).toBeInTheDocument();
    expectNoForbiddenCopy();
  });

  it('replaces the result with a new description', async () => {
    render(<App />);
    submitSituation('overload in the west');
    await screen.findByRole('region', { name: thermal.title });
    submitSituation('Low voltage in the north-west at the evening ramp');
    const region = await screen.findByRole('region', { name: voltage.title });
    expect(within(region).getByText(/Storage B to charging at 20 MW/)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: thermal.title })).not.toBeInTheDocument();
  });

  it('shows no action when the scenario has none', async () => {
    render(<App />);
    submitSituation('SNSP overnight');
    const region = await screen.findByRole('region', { name: snsp.title });
    expect(within(region).getByText(WORKSPACE_COPY.actionNone)).toBeInTheDocument();
    expect(within(region).getByText(snsp.noActionReason as string)).toBeInTheDocument();
  });

  it('says so when nothing matches', async () => {
    render(<App />);
    submitSituation('xyzzy plugh');
    expect(await screen.findByText(WORKSPACE_COPY.noMatchTitle)).toBeInTheDocument();
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
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
});

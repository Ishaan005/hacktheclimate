import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SAFETY_COPY } from '../../decision/copy/safety';
import { STALE_NOTE } from '../../decision/copy/shared';
import { fixtureAssessment } from '../../decision/fixture';
import type { Assessment, SafetyCheck, ViewMode } from '../../decision/types';
import SafetyPanel from './SafetyPanel';

function renderPanel(assessment: Assessment = fixtureAssessment, view: ViewMode = 'national') {
  return render(
    <SafetyPanel assessment={assessment} overall={assessment.overall} plan={assessment.proposed} view={view} />,
  );
}

function row(container: HTMLElement, checkId: string): HTMLElement {
  const found = container.querySelector<HTMLElement>(`li[data-check-id="${checkId}"]`);
  if (!found) throw new Error(`No row for ${checkId}`);
  return found;
}

function unknownCheck(id: string, reason: string): SafetyCheck {
  return {
    id, label: `Check ${id}`, family: 'transmission', value: null, limit: null, margin: null,
    worstTime: null, worstFailure: null, source: null, result: 'unknown', reason,
  };
}

describe('safety panel', () => {
  it('shows quantified demo safety results while naming the unresolved checks', () => {
    const { container } = render(<SafetyPanel assessment={fixtureAssessment} overall={fixtureAssessment.overall}
      plan={fixtureAssessment.proposed} view="national" demo />);
    const cards = [...container.querySelectorAll<HTMLElement>('[data-key-check]')];
    expect(cards.map((card) => card.dataset.keyCheck)).toEqual(['fc-flow', 'fc-relief', 'fc-snsp']);
    expect(cards[0]).toHaveTextContent('406 MW');
    expect(cards[1]).toHaveTextContent('20 min');
    expect(cards[2]).toHaveTextContent('72.4%');
    expect(cards.every((card) => !card.textContent?.includes('No result'))).toBe(true);
    expect(container.querySelector('.safety-pending'))
      .toHaveTextContent('Safety not yet established. Still unverified: Worst flow after one further failure; Inertia and RoCoF.');
  });

  it('pairs technical safety terms with plain descriptions in the key cards', () => {
    const { container } = renderPanel();
    expect(container.querySelector('[data-key-check="fc-n1"]')).toHaveTextContent('Contingency loading (worst flow after one further failure)');
    expect(container.querySelector('[data-key-check="fc-stability"]')).toHaveTextContent('Frequency stability (inertia and RoCoF)');
  });

  it('shows available baseline and proposed metrics without empty check sections', () => {
    const current = { ...fixtureAssessment.familyChecks[0], id: 'planning_line',
      label: 'Transmission line loading', value: '109.1% of rate A', limit: '100% of rate A',
      margin: '-5 MW', result: 'fail' as const };
    const proposed = { ...current, value: '81.8% of rate A', margin: '+10 MW', result: 'pass' as const };
    const assessment = { ...fixtureAssessment, currentChecks: [current], familyChecks: [proposed],
      actionChecks: fixtureAssessment.actionChecks.map((check) => ({ ...check, value: null, margin: null })) };
    const { container } = render(<SafetyPanel assessment={assessment} overall={assessment.overall}
      plan={assessment.proposed} view="national" demo />);
    const metric = container.querySelector('[data-metric-id="planning_line"]') as HTMLElement;
    expect(metric).toHaveTextContent('109.1% of rate A');
    expect(metric).toHaveTextContent('81.8% of rate A');
    expect(metric).toHaveTextContent('Margin -5 MW');
    expect(metric).toHaveTextContent('Margin +10 MW');
    expect(metric).toHaveTextContent('Limit 100% of rate A');
    expect(screen.queryByRole('heading', { name: SAFETY_COPY.actionChecksTitle })).toBeNull();
  });

  it('omits unquantified demo checks and hides old plan figures while edits are stale', () => {
    const current = { ...fixtureAssessment.familyChecks[0], id: 'line', value: '0 MW', margin: null };
    const unknown = { ...fixtureAssessment.familyChecks[0], id: 'snsp', value: null, margin: null, limit: '75%' };
    const assessment = { ...fixtureAssessment, currentChecks: [current, unknown], familyChecks: [
      { ...current, value: '10 MW' }, unknown,
    ] };
    const { container } = render(<SafetyPanel assessment={assessment} overall={assessment.overall}
      plan={assessment.proposed} view="national" demo stale />);
    expect(container.querySelector('[data-metric-id="line"]')).toHaveTextContent('0 MW');
    expect(container.querySelector('[data-metric-id="line"]')).not.toHaveTextContent('10 MW');
    expect(container.querySelector('[data-metric-id="snsp"]')).toBeNull();
  });

  it('shows one short empty state when the API has no quantified safety checks', () => {
    const assessment = { ...fixtureAssessment, currentChecks: [], familyChecks: [], actionChecks: [] };
    render(<SafetyPanel assessment={assessment} overall={assessment.overall}
      plan={assessment.proposed} view="national" demo />);
    expect(screen.getByText('No quantified safety checks for this case.')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: SAFETY_COPY.actionChecksTitle })).toBeNull();
  });

  it('shows the overall result in the header with its reason and no evidence list or validation warning', () => {
    renderPanel(fixtureAssessment, 'national');
    const panel = screen.getByRole('region', { name: SAFETY_COPY.title });
    const header = within(panel).getByRole('heading', { level: 2, name: SAFETY_COPY.title }).parentElement as HTMLElement;
    expect(within(header).getByText('Unknown')).toBeInTheDocument();
    expect(within(panel).getByText(fixtureAssessment.overall.reason)).toBeInTheDocument();
    expect(within(panel).queryByText(STALE_NOTE)).not.toBeInTheDocument();
    for (const item of fixtureAssessment.overall.missingEvidence) {
      expect(within(panel).queryByText(item)).toBeNull();
    }
    expect(panel.textContent).not.toMatch(/validated/i);
  });

  it('displays the overall result exactly as given', () => {
    render(
      <SafetyPanel
        assessment={fixtureAssessment}
        overall={{ result: 'fail', reason: 'Given by the caller.', missingEvidence: [] }}
        plan={null}
        view="national"
      />,
    );
    const header = screen.getByRole('heading', { level: 2, name: SAFETY_COPY.title }).parentElement as HTMLElement;
    expect(within(header).getByText('Fail')).toBeInTheDocument();
    expect(screen.getByText('Given by the caller.')).toBeInTheDocument();
    expect(screen.getByText(SAFETY_COPY.noPlan)).toBeInTheDocument();
  });

  it('shows one constraint family at a time from a menu that states every family result', () => {
    const { container } = renderPanel();
    const menu = screen.getByRole('combobox', { name: SAFETY_COPY.familyMenuLabel });
    const options = within(menu).getAllByRole('option').map((option) => option.textContent);
    expect(options).toEqual(['Transmission constraint (1 unknown, 2 pass)', 'SNSP (1 unknown, 1 pass)']);
    expect(container.querySelector('li[data-check-id="fc-flow"]')).not.toBeNull();
    expect(container.querySelector('li[data-check-id="fc-snsp"]')).toBeNull();
    fireEvent.change(menu, { target: { value: 'snsp' } });
    expect(container.querySelector('li[data-check-id="fc-snsp"]')).not.toBeNull();
    expect(container.querySelector('li[data-check-id="fc-flow"]')).toBeNull();
  });

  it('opens on the first family with a failed check', () => {
    const { container } = renderPanel({
      ...fixtureAssessment,
      familyChecks: fixtureAssessment.familyChecks.map((check) => (check.id === 'fc-snsp' ? { ...check, result: 'fail' } : check)),
    });
    expect(screen.getByRole('combobox', { name: SAFETY_COPY.familyMenuLabel })).toHaveValue('snsp');
    expect(container.querySelector('li[data-check-id="fc-snsp"]')).not.toBeNull();
  });

  it('shows Fail on a failing family check', () => {
    const { container } = renderPanel({
      ...fixtureAssessment,
      familyChecks: fixtureAssessment.familyChecks.map((check) => (check.id === 'fc-flow' ? { ...check, result: 'fail' } : check)),
    });
    expect(within(row(container, 'fc-flow')).getByText('Fail')).toBeInTheDocument();
  });

  it('sorts fail rows before unknown and pass within a family', () => {
    const { container } = renderPanel({
      ...fixtureAssessment,
      familyChecks: fixtureAssessment.familyChecks.map((check) => (check.id === 'fc-relief' ? { ...check, result: 'fail' } : check)),
    });
    const family = container.querySelector('[data-family="transmission"]') as HTMLElement;
    const ids = [...family.querySelectorAll('li[data-check-id]')].map((item) => item.getAttribute('data-check-id'));
    expect(ids).toEqual(['fc-relief', 'fc-n1', 'fc-flow']);
  });

  it('shows the worst credible failure for transmission checks', () => {
    const { container } = renderPanel();
    const failure = row(container, 'fc-n1').querySelector('[data-field="worstFailure"]');
    expect(failure).toHaveTextContent(SAFETY_COPY.fields.worstFailure);
    expect(failure).toHaveTextContent('Flagford–Srananagh 220 kV');
  });

  it('omits null fields and never renders them as 0', () => {
    const { container } = renderPanel();
    const partial = row(container, 'fc-n1');
    expect(partial.querySelector('[data-field="value"]')).toBeNull();
    expect(partial.querySelector('[data-field="margin"]')).toBeNull();
    expect(partial.querySelector('[data-field="limit"]')).toHaveTextContent('431 MVA');
    fireEvent.change(screen.getByRole('combobox', { name: SAFETY_COPY.familyMenuLabel }), { target: { value: 'snsp' } });
    const empty = row(container, 'fc-stability');
    expect(empty.querySelector('.safety-check-figures')).toBeNull();
    expect(empty.querySelector('.safety-check-meta')).toBeNull();
    expect(empty).not.toHaveTextContent('Not available');
    expect(empty).not.toHaveTextContent('0');
    expect(within(empty).getByText('Unknown')).toBeInTheDocument();
  });

  it('states a shared unknown reason once and keeps every check listed', () => {
    const reason = 'Validated assessment not connected';
    const shared = ['x1', 'x2', 'x3'].map((id) => unknownCheck(id, reason));
    const { container } = renderPanel({ ...fixtureAssessment, familyChecks: [...fixtureAssessment.familyChecks, ...shared] });
    expect(screen.getAllByText(new RegExp(reason)).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(`${SAFETY_COPY.sharedReason(3)} ${reason}`)).toBeInTheDocument();
    for (const check of shared) {
      expect(within(row(container, check.id)).getByText('Unknown')).toBeInTheDocument();
    }
  });

  it('shows all-island limits in site view only', () => {
    const { unmount } = renderPanel(fixtureAssessment, 'site');
    const section = screen.getByRole('region', { name: SAFETY_COPY.allIslandTitle });
    expect(section.closest('details')).not.toBeNull();
    expect(within(section).getByText('Below the effective limit.')).toBeInTheDocument();
    unmount();
    renderPanel(fixtureAssessment, 'national');
    expect(screen.queryByRole('region', { name: SAFETY_COPY.allIslandTitle })).toBeNull();
  });

  it('lists action checks only for steps in the plan, go/no-go first', () => {
    const [match, range, ...rest] = fixtureAssessment.actionChecks;
    const assessment: Assessment = {
      ...fixtureAssessment,
      // Non-go/no-go listed first to prove the panel reorders it.
      actionChecks: [range, match, ...rest, { ...match, id: 'ac-other-plan', stepId: 'step-9', label: 'Check for another plan' }],
    };
    const { container } = renderPanel(assessment);
    expect(container.querySelector('li[data-check-id="ac-other-plan"]')).toBeNull();
    expect(screen.queryByText('Check for another plan')).toBeNull();
    expect(container.querySelectorAll('details.safety-step')).toHaveLength(2);
    const step = container.querySelector('details[data-step-id="step-1"]') as HTMLElement;
    const rows = step.querySelectorAll('li[data-check-id]');
    expect(rows[0]).toHaveAttribute('data-check-id', 'ac-redispatch-match');
    expect(within(rows[0] as HTMLElement).getByText(SAFETY_COPY.goNoGo)).toBeInTheDocument();
    expect(rows[1]).toHaveAttribute('data-check-id', 'ac-redispatch-range');
    expect(screen.getByText(SAFETY_COPY.actionChecksNote)).toBeInTheDocument();
  });
});

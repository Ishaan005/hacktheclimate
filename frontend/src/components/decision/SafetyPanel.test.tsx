import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SAFETY_COPY } from '../../decision/copy/safety';
import { STALE_NOTE } from '../../decision/copy/shared';
import { fixtureAssessment } from '../../decision/fixture';
import type { Assessment, ViewMode } from '../../decision/types';
import SafetyPanel from './SafetyPanel';

function renderPanel(assessment: Assessment = fixtureAssessment, view: ViewMode = 'national', stale = false) {
  return render(
    <SafetyPanel assessment={assessment} overall={assessment.overall} plan={assessment.proposed} view={view} stale={stale} />,
  );
}

function row(container: HTMLElement, checkId: string): HTMLElement {
  const found = container.querySelector<HTMLElement>(`tr[data-check-id="${checkId}"]`);
  if (!found) throw new Error(`No row for ${checkId}`);
  return found;
}

describe('safety panel', () => {
  it('shows Unknown with the missing evidence and demonstration note', () => {
    renderPanel(fixtureAssessment, 'national', true);
    const overall = screen.getByText(SAFETY_COPY.overallLabel, { selector: '.safety-overall-label' }).closest('.safety-overall') as HTMLElement;
    expect(within(overall).getByText('Unknown')).toBeInTheDocument();
    expect(within(overall).getByText(SAFETY_COPY.missingEvidence)).toBeInTheDocument();
    for (const item of fixtureAssessment.overall.missingEvidence) {
      expect(within(overall).getByText(item)).toBeInTheDocument();
    }
    expect(within(overall).getByText(STALE_NOTE)).toBeInTheDocument();
    expect(within(overall).getByText(SAFETY_COPY.notValidated)).toBeInTheDocument();
  });

  it('shows Fail on a failing family check', () => {
    const { container } = renderPanel({
      ...fixtureAssessment,
      familyChecks: fixtureAssessment.familyChecks.map((check) => (check.id === 'fc-flow' ? { ...check, result: 'fail' } : check)),
    });
    expect(within(row(container, 'fc-flow')).getByText('Fail')).toBeInTheDocument();
  });

  it('shows the worst credible failure for transmission checks', () => {
    const { container } = renderPanel();
    const cell = row(container, 'fc-n1').querySelector(`td[data-label="${SAFETY_COPY.columns.worstFailure}"]`);
    expect(cell).toHaveTextContent('Flagford–Srananagh 220 kV');
  });

  it('shows all-island limits in site view only', () => {
    const { unmount } = renderPanel(fixtureAssessment, 'site');
    const section = screen.getByRole('region', { name: SAFETY_COPY.allIslandTitle });
    expect(section.closest('details')).toBeNull();
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
    expect(container.querySelector('tr[data-check-id="ac-other-plan"]')).toBeNull();
    expect(screen.queryByText('Check for another plan')).toBeNull();
    expect(container.querySelectorAll('details.safety-step')).toHaveLength(2);
    const step = container.querySelector('details[data-step-id="step-1"]') as HTMLElement;
    const rows = step.querySelectorAll('tbody tr');
    expect(rows[0]).toHaveAttribute('data-check-id', 'ac-redispatch-match');
    expect(rows[1]).toHaveAttribute('data-check-id', 'ac-redispatch-range');
    expect(screen.getByText(SAFETY_COPY.actionChecksNote)).toBeInTheDocument();
  });

  it('renders a missing value as Not available, never 0', () => {
    const { container } = renderPanel();
    const cell = row(container, 'fc-n1').querySelector(`td[data-label="${SAFETY_COPY.columns.value}"]`);
    expect(cell).toHaveTextContent(SAFETY_COPY.notAvailable);
    expect(cell).not.toHaveTextContent('0');
  });
});

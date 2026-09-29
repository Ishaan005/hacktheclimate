import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PLAN_COPY } from '../../decision/copy/plan';
import { PLAN_LABEL, STALE_NOTE } from '../../decision/copy/shared';
import { fixtureAssessment } from '../../decision/fixture';
import type { Assessment, Plan, PlanStep, SafetyCheck } from '../../decision/types';
import { copyAsAlternative } from '../../decision/useDecisionWorkspace';
import PlanPanel from './PlanPanel';

type RenderOptions = { alternative?: Plan | null; stale?: boolean };

function renderPanel(assessment: Assessment, { alternative = null, stale = false }: RenderOptions = {}) {
  const handlers = { onEditStep: vi.fn(), onSetAlternative: vi.fn(), onRerun: vi.fn() };
  render(<PlanPanel assessment={assessment} alternative={alternative} stale={stale} {...handlers} />);
  return handlers;
}

function proposedSection() {
  return screen.getByRole('region', { name: PLAN_COPY.proposedHeading });
}

const pass = <T extends SafetyCheck>(check: T): T => ({ ...check, result: 'pass' });

// A validated assessment where every check passes and every fact is current.
// Only the permission state on the main step decides between Conditional and
// Actionable.
function cleanAssessment(permissionState: PlanStep['permissionState']): Assessment {
  const proposed = fixtureAssessment.proposed as Plan;
  return {
    ...fixtureAssessment,
    validated: true,
    overall: { result: 'pass', reason: 'All required checks pass.', missingEvidence: [] },
    facts: fixtureAssessment.facts.map((fact) => ({ ...fact, state: 'current' })),
    familyChecks: fixtureAssessment.familyChecks.map(pass),
    crossChecks: fixtureAssessment.crossChecks.map(pass),
    allIslandChecks: fixtureAssessment.allIslandChecks.map(pass),
    actionChecks: fixtureAssessment.actionChecks.map(pass),
    proposed: {
      ...proposed,
      label: 'actionable',
      labelReason: 'Backend: all checks pass.',
      steps: proposed.steps.map((step) => ({
        ...step,
        blockingCheckIds: [],
        permissionState: step.permissionRoute === 'direct' ? 'confirmed' : permissionState,
      })),
    },
  };
}

describe('plan panel', () => {
  it('shows the main step before supporting steps, even when listed later', () => {
    const proposed = fixtureAssessment.proposed as Plan;
    const reordered: Assessment = { ...fixtureAssessment, proposed: { ...proposed, steps: [...proposed.steps].reverse() } };
    renderPanel(reordered);
    const steps = within(proposedSection()).getAllByRole('listitem');
    expect(steps[0]).toHaveTextContent('Main action');
    expect(steps[0]).toHaveTextContent('Reduce Wind Farm A by 40 MW');
    expect(steps[1]).toHaveTextContent('Supporting step');
    expect(steps[1]).toHaveTextContent('Charge Battery B at 15 MW.');
  });

  it('shows the MW effect with MW and never MWh or energy saved', () => {
    renderPanel(fixtureAssessment);
    const section = proposedSection();
    expect(within(section).getByText('−32 MW')).toBeInTheDocument();
    expect(within(section).getByText('−12 MW')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: PLAN_COPY.title }).textContent).not.toMatch(/MWh|energy saved/i);
  });

  it('shows who does each step, permission, timing and blockers', () => {
    renderPanel(fixtureAssessment);
    const [main, supporting] = within(proposedSection()).getAllByRole('listitem');
    expect(main).toHaveTextContent('Wind Farm A / Tynagh CCGT');
    expect(main).toHaveTextContent('Needs acceptance by Tynagh generator owner');
    expect(main).toHaveTextContent('Pending');
    expect(main).toHaveTextContent('16:00');
    expect(main).toHaveTextContent('16:20');
    expect(main).toHaveTextContent('120 min');
    // A pending acceptance counts as a blocker.
    expect(main).toHaveTextContent('Permission from Tynagh generator owner (pending)');
    expect(supporting).toHaveTextContent('Direct instruction');
    expect(supporting).toHaveTextContent('1 safety check needs evidence');
  });

  it('shows dependencies between steps', () => {
    renderPanel(fixtureAssessment);
    const supporting = within(proposedSection()).getAllByRole('listitem')[1];
    expect(supporting).toHaveTextContent('Starts after: Reduce Wind Farm A by 40 MW; increase Tynagh CCGT by 40 MW.');
  });

  it('is never Actionable with a failed or unknown check', () => {
    const failing: Assessment = {
      ...fixtureAssessment,
      familyChecks: fixtureAssessment.familyChecks.map((check, i) => (i === 0 ? { ...check, result: 'fail' } : check)),
    };
    renderPanel(failing);
    expect(within(proposedSection()).getByText(PLAN_LABEL.unsafe)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
  });

  it('shows Insufficient evidence when a required check is unknown', () => {
    const clean = cleanAssessment('confirmed');
    const unknown: Assessment = {
      ...clean,
      familyChecks: clean.familyChecks.map((check, i) => (i === 0 ? { ...check, result: 'unknown' } : check)),
    };
    renderPanel(unknown);
    expect(within(proposedSection()).getByText(PLAN_LABEL.insufficient_evidence)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
  });

  it('stays Conditional until acceptance is recorded, then shows Actionable', () => {
    renderPanel(cleanAssessment('pending'));
    expect(within(proposedSection()).getByText(PLAN_LABEL.conditional)).toBeInTheDocument();
    expect(within(proposedSection()).getByText(/Waiting for Tynagh generator owner to accept/)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
  });

  it('shows Actionable once the other party has confirmed', () => {
    renderPanel(cleanAssessment('confirmed'));
    expect(within(proposedSection()).getByText(PLAN_LABEL.actionable)).toBeInTheDocument();
  });

  it('is not Actionable while stale, and offers a rerun', () => {
    const { onRerun } = renderPanel(cleanAssessment('confirmed'), { stale: true });
    expect(screen.getByText(STALE_NOTE)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: PLAN_COPY.rerun }));
    expect(onRerun).toHaveBeenCalledTimes(1);
  });

  it('creates an operator alternative and leaves the proposal unchanged', () => {
    const { onSetAlternative } = renderPanel(fixtureAssessment);
    fireEvent.click(screen.getByRole('button', { name: PLAN_COPY.editAsAlternative }));
    expect(onSetAlternative).toHaveBeenCalledTimes(1);
    const created = onSetAlternative.mock.calls[0][0] as Plan;
    expect(created.origin).toBe('operator');
    expect(created.steps).toHaveLength(2);
    expect(fixtureAssessment.proposed?.origin).toBe('proposed');
  });

  it('edits, removes and discards alternative steps while the proposal stays visible', () => {
    const alternative = copyAsAlternative(fixtureAssessment.proposed) as Plan;
    const { onEditStep, onSetAlternative } = renderPanel(fixtureAssessment, { alternative });
    expect(within(proposedSection()).getAllByRole('listitem')).toHaveLength(2);
    const section = screen.getByRole('region', { name: PLAN_COPY.alternativeHeading });
    const [main] = within(section).getAllByRole('listitem');

    fireEvent.change(within(main).getByLabelText(PLAN_COPY.edit.instruction), { target: { value: 'Reduce Wind Farm A by 30 MW.' } });
    expect(onEditStep).toHaveBeenLastCalledWith('step-1', { instruction: 'Reduce Wind Farm A by 30 MW.' });

    fireEvent.change(within(main).getByLabelText(PLAN_COPY.edit.mwEffect), { target: { value: '-25' } });
    expect(onEditStep).toHaveBeenLastCalledWith('step-1', { mwEffect: -25 });

    fireEvent.change(within(main).getByLabelText(PLAN_COPY.edit.mwEffect), { target: { value: '' } });
    expect(onEditStep).toHaveBeenLastCalledWith('step-1', { mwEffect: null });

    fireEvent.change(within(main).getByLabelText(PLAN_COPY.edit.startTime), { target: { value: '2026-01-24T16:10' } });
    expect(onEditStep).toHaveBeenLastCalledWith('step-1', { startTime: '2026-01-24T16:10:00.000Z' });

    fireEvent.change(within(main).getByLabelText(PLAN_COPY.edit.permissionState), { target: { value: 'confirmed' } });
    expect(onEditStep).toHaveBeenLastCalledWith('step-1', { permissionState: 'confirmed' });

    fireEvent.click(within(main).getByRole('button', { name: PLAN_COPY.removeStep }));
    const kept = onSetAlternative.mock.lastCall as [Plan];
    expect(kept[0].steps.map((step) => step.id)).toEqual(['step-2']);

    fireEvent.click(within(section).getByRole('button', { name: PLAN_COPY.discardAlternative }));
    expect(onSetAlternative).toHaveBeenLastCalledWith(null);
  });

  it('never offers a button that sends an instruction, and says so', () => {
    const alternative = copyAsAlternative(fixtureAssessment.proposed);
    renderPanel(fixtureAssessment, { alternative, stale: true });
    for (const button of screen.getAllByRole('button')) {
      expect(button).not.toHaveAccessibleName(/send|issue|dispatch/i);
    }
    expect(screen.getByText(PLAN_COPY.noSendNote)).toBeInTheDocument();
  });

  it('explains when there is no proposed plan', () => {
    renderPanel({ ...fixtureAssessment, proposed: null });
    expect(screen.getByText(PLAN_COPY.noPlan)).toBeInTheDocument();
    expect(screen.getByText(fixtureAssessment.overall.reason)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: PLAN_COPY.editAsAlternative })).not.toBeInTheDocument();
  });
});

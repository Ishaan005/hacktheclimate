import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PLAN_COPY } from '../../decision/copy/plan';
import { PLAN_LABEL, STALE_NOTE } from '../../decision/copy/shared';
import { fixtureAssessment } from '../../decision/fixture';
import { planLabel } from '../../decision/rules';
import type { Assessment, Plan, PlanStep, SafetyCheck } from '../../decision/types';
import { copyAsAlternative } from '../../decision/useDecisionWorkspace';
import PlanPanel from './PlanPanel';

type RenderOptions = { alternative?: Plan | null; stale?: boolean };

function renderPanel(assessment: Assessment, { alternative = null, stale = false }: RenderOptions = {}) {
  const handlers = { onEditStep: vi.fn(), onSetAlternative: vi.fn() };
  render(<PlanPanel assessment={assessment} alternative={alternative} stale={stale} {...handlers} />);
  return handlers;
}

function proposedSection() {
  return screen.getByRole('region', { name: PLAN_COPY.proposedHeading });
}

function panel() {
  return screen.getByRole('region', { name: PLAN_COPY.title });
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
    expect(steps[0]).toHaveTextContent('Redispatch');
    expect(steps[0]).toHaveTextContent('Reduce Wind Farm A by 40 MW');
    expect(steps[1]).toHaveTextContent('Battery charging');
    expect(steps[1]).toHaveTextContent('Charge Battery B at 15 MW.');
    expect(steps[0]).not.toHaveTextContent('Step 1');
    expect(steps[1]).not.toHaveTextContent('Step 2');
  });

  it('shows the expected route relief as green MW saved with a blue relief label', () => {
    renderPanel(fixtureAssessment);
    const section = proposedSection();
    const saved = within(section).getByText('44 MW saved');
    expect(saved).toHaveClass('plan-outcome-saved');
    expect(within(section).getByText('Expected route relief')).toHaveClass('plan-outcome-relief');
    expect(panel().textContent).not.toMatch(/MWh/i);
  });

  it('shows where each step happens and its timing without permission fields', () => {
    renderPanel(fixtureAssessment);
    const [main, supporting] = within(proposedSection()).getAllByRole('listitem');
    expect(main).toHaveTextContent('Wind Farm A / Tynagh CCGT');
    expect(main).toHaveTextContent('Where / who');
    expect(main).toHaveTextContent('16:00');
    expect(main).toHaveTextContent('16:20');
    expect(main).toHaveTextContent('120 min');
    expect(main).not.toHaveTextContent('Permission');
    expect(supporting).toHaveTextContent('Battery B');
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
    expect(within(panel()).getByText(PLAN_LABEL.unsafe)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
  });

  it('shows Insufficient evidence when a required check is unknown', () => {
    const clean = cleanAssessment('confirmed');
    const unknown: Assessment = {
      ...clean,
      familyChecks: clean.familyChecks.map((check, i) => (i === 0 ? { ...check, result: 'unknown' } : check)),
    };
    renderPanel(unknown);
    expect(within(panel()).getByText(PLAN_LABEL.insufficient_evidence)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
  });

  it('stays Conditional until acceptance is recorded, then shows Actionable', () => {
    renderPanel(cleanAssessment('pending'));
    expect(within(panel()).getByText(PLAN_LABEL.conditional)).toBeInTheDocument();
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
  });

  it('shows Actionable once the other party has confirmed', () => {
    renderPanel(cleanAssessment('confirmed'));
    expect(within(panel()).getByText(PLAN_LABEL.actionable)).toBeInTheDocument();
  });

  it('is not Actionable while stale, and leaves the out-of-date notice to the summary', () => {
    renderPanel(cleanAssessment('confirmed'), { stale: true });
    expect(screen.queryByText(PLAN_LABEL.actionable)).not.toBeInTheDocument();
    expect(screen.queryByText(STALE_NOTE)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /rerun/i })).not.toBeInTheDocument();
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

  it('never offers a button that sends an instruction', () => {
    const alternative = copyAsAlternative(fixtureAssessment.proposed);
    renderPanel(fixtureAssessment, { alternative, stale: true });
    for (const button of screen.getAllByRole('button')) {
      expect(button).not.toHaveAccessibleName(/send|issue|dispatch/i);
    }
  });

  it('explains when there is no proposed plan in one short line', () => {
    renderPanel({ ...fixtureAssessment, proposed: null });
    const line = screen.getByText(new RegExp(`^${PLAN_COPY.noPlan}\\.`));
    expect(line).toHaveTextContent(PLAN_COPY.noPlanReason[fixtureAssessment.overall.result]);
    expect(screen.getAllByText(new RegExp(PLAN_COPY.noPlan))).toHaveLength(1);
    // The safety panel gives the full reason; the plan panel does not repeat it.
    expect(panel().textContent).not.toContain(fixtureAssessment.overall.reason);
    expect(screen.queryByRole('button', { name: PLAN_COPY.editAsAlternative })).not.toBeInTheDocument();
  });

  it('offers a labelled operator alternative when there is no proposed plan', () => {
    const { onSetAlternative } = renderPanel({ ...fixtureAssessment, proposed: null });
    const select = screen.getByRole('combobox', { name: PLAN_COPY.buildAlternative });
    fireEvent.change(select, { target: { value: 'paired_redispatch' } });
    const create = screen.getByRole('button', { name: PLAN_COPY.createAlternative });
    expect(create).toHaveClass('button-secondary');
    fireEvent.click(create);
    const created = onSetAlternative.mock.calls[0][0] as Plan;
    expect(created.origin).toBe('operator');
    expect(created.steps.map((step) => step.kind)).toEqual(['paired_redispatch']);
  });

  it('puts the panel title and the proposal label in one header', () => {
    renderPanel(fixtureAssessment);
    const heading = screen.getByRole('heading', { level: 2, name: PLAN_COPY.title });
    expect(heading).toHaveClass('panel-title');
    const header = heading.closest('.panel-header') as HTMLElement;
    const { label } = planLabel(fixtureAssessment.proposed as Plan, fixtureAssessment, false);
    expect(within(header).getByText(PLAN_LABEL[label])).toBeInTheDocument();
  });

  it('leads each step with its instruction and timing', () => {
    renderPanel(fixtureAssessment);
    const [main, supporting] = within(proposedSection()).getAllByRole('listitem');
    expect(within(main).getByRole('heading', { level: 4 })).toHaveTextContent('Reduce Wind Farm A by 40 MW; increase Tynagh CCGT by 40 MW.');
    expect(main).toHaveClass('plan-step-conditional');
    expect(supporting).not.toHaveClass('plan-step-conditional');
    for (const label of [PLAN_COPY.fields.startTime, PLAN_COPY.fields.effectTime, PLAN_COPY.fields.duration]) {
      expect(within(main).getByText(label)).toBeInTheDocument();
    }
  });

  it('has at most one primary button, and removal is never primary', () => {
    const alternative = copyAsAlternative(fixtureAssessment.proposed);
    const { container } = render(
      <PlanPanel assessment={fixtureAssessment} alternative={alternative} stale onEditStep={vi.fn()} onSetAlternative={vi.fn()} />,
    );
    expect(container.querySelectorAll('.button-primary').length).toBeLessThanOrEqual(1);
    for (const name of [PLAN_COPY.removeStep, PLAN_COPY.discardAlternative]) {
      for (const button of screen.getAllByRole('button', { name })) {
        expect(button).not.toHaveClass('button-primary');
      }
    }
  });
});

import { ACTION_FAMILY_LABEL, EXECUTABILITY_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import { instructionText } from '../scenarios';
import type { ActionStep, RecommendedAction } from '../types';
import ActionTimeline from './ActionTimeline';

type Props = {
  action: RecommendedAction | null;
  noActionReason: string | null;
  presentation?: 'recommended' | 'modeled_candidate';
};

// Expands in place under the overview; the card grows to fit.
function ActionSteps({ steps }: { steps: ActionStep[] }) {
  return (
    <details className="action-steps">
      <summary>{WORKSPACE_COPY.actionStepsTitle} ({steps.length})</summary>
      <ol className="action-steps-panel">
        {steps.map((step, i) => (
          <li key={i}>
            <span className="action-step-time mono">{step.time ? formatTime(step.time) : '—'}</span>
            <span>{step.text}</span>
          </li>
        ))}
      </ol>
    </details>
  );
}

// Overview only: the complete instruction, any conditional warning, the state
// change and the schedule strip. The ordered steps sit in a dropdown list.
function RecommendedActionCard({ action, noActionReason, presentation = 'recommended' }: Props) {
  if (!action) {
    return (
      <section className="card card-action card-action-none" aria-labelledby="action-heading">
        <h3 id="action-heading" className="card-kicker">{WORKSPACE_COPY.actionTitle}</h3>
        <p className="card-headline">{WORKSPACE_COPY.actionNone}</p>
        {noActionReason && <p>{noActionReason}</p>}
      </section>
    );
  }
  const conditional = action.executability === 'conditional';
  const steps = action.steps ?? [];
  return (
    <section
      className={`card card-action${conditional ? ' card-action-conditional' : ''}`}
      aria-labelledby="action-heading"
    >
      <h3 id="action-heading" className="card-kicker">
        {presentation === 'modeled_candidate' ? WORKSPACE_COPY.modeledCandidateTitle : WORKSPACE_COPY.actionTitle}
        <span className="chip chip-neutral">{ACTION_FAMILY_LABEL[action.family]}</span>
        <span className={`chip ${conditional ? 'chip-unknown' : 'chip-neutral'}`}>{EXECUTABILITY_LABEL[action.executability]}</span>
      </h3>
      <p className="instruction">{presentation === 'modeled_candidate'
        ? `Modeled bundle — ${action.assetName}: ${action.targetState} by ${formatTime(action.targetTime)}, through ${formatTime(action.effectiveUntil)}.`
        : instructionText(action)}</p>
      {conditional && <p className="action-warning">{WORKSPACE_COPY.actionConditional}</p>}
      <p className="state-change">
        <span className="state-change-asset">{action.assetName} · {action.location}</span>
        <span className="state-change-values">
          <span className="state-change-from">{action.currentState}</span>
          <span aria-hidden="true">→</span>
          <span className="visually-hidden">to</span>
          <span className="state-change-to">{action.targetState}</span>
        </span>
      </p>
      <ActionTimeline action={action} />
      {steps.length > 0 && <ActionSteps steps={steps} />}
    </section>
  );
}

export default RecommendedActionCard;

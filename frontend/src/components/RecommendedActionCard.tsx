import { useEffect, useRef } from 'react';
import { ACTION_FAMILY_LABEL, EXECUTABILITY_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import { instructionText } from '../scenarios';
import type { ActionStep, RecommendedAction } from '../types';
import ActionTimeline from './ActionTimeline';

type Props = {
  action: RecommendedAction | null;
  noActionReason: string | null;
};

// A dropdown panel that floats over the content below, so opening it never
// changes the card height. Closes on Escape or a click outside.
function ActionSteps({ steps }: { steps: ActionStep[] }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    function close(event: Event) {
      const details = ref.current;
      if (!details?.open) return;
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !details.contains(event.target as Node)) {
        details.open = false;
      }
    }
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, []);
  return (
    <details ref={ref} className="action-steps">
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
function RecommendedActionCard({ action, noActionReason }: Props) {
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
  return (
    <section
      className={`card card-action${conditional ? ' card-action-conditional' : ''}`}
      aria-labelledby="action-heading"
    >
      <h3 id="action-heading" className="card-kicker">
        {WORKSPACE_COPY.actionTitle}
        <span className="chip chip-neutral">{ACTION_FAMILY_LABEL[action.family]}</span>
        <span className={`chip ${conditional ? 'chip-unknown' : 'chip-neutral'}`}>{EXECUTABILITY_LABEL[action.executability]}</span>
      </h3>
      <p className="instruction">{instructionText(action)}</p>
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
      {action.steps.length > 0 && <ActionSteps steps={action.steps} />}
    </section>
  );
}

export default RecommendedActionCard;

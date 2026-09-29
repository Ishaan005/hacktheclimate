import { ACTION_FAMILY_LABEL, EXECUTABILITY_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import { instructionText } from '../scenarios';
import type { RecommendedAction } from '../types';
import ActionDetails from './ActionDetails';
import ActionTimeline from './ActionTimeline';

type Props = {
  action: RecommendedAction | null;
  noActionReason: string | null;
};

// Shared shell: the complete instruction first, then the state change and a
// schedule strip. The full field list and family-specific detail sit behind
// the disclosure.
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
      <details className="action-details">
        <summary>{WORKSPACE_COPY.actionDetailsSummary}: {ACTION_FAMILY_LABEL[action.family]}</summary>
        <div className="action-detail">
          <dl className="fields fields-action">
            <div><dt>Asset</dt><dd>{action.assetName}</dd></div>
            <div><dt>Location</dt><dd>{action.location}</dd></div>
            <div><dt>Current state</dt><dd>{action.currentState}</dd></div>
            <div><dt>Target state</dt><dd>{action.targetState}</dd></div>
            <div><dt>Issue time</dt><dd className="mono">{formatTime(action.issueTime)}</dd></div>
            <div><dt>Start time</dt><dd className="mono">{formatTime(action.startTime)}</dd></div>
            <div><dt>Target achieved</dt><dd className="mono">{formatTime(action.targetTime)}</dd></div>
            <div><dt>Effective until</dt><dd className="mono">{formatTime(action.effectiveUntil)}</dd></div>
            <div>
              <dt>Earliest achievable execution</dt>
              <dd className="mono">{action.earliestExecution ? formatTime(action.earliestExecution) : 'Unknown'}</dd>
            </div>
          </dl>
        </div>
        <ActionDetails action={action} />
      </details>
    </section>
  );
}

export default RecommendedActionCard;

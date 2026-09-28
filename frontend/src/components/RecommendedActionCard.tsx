import { ACTION_FAMILY_LABEL, EXECUTABILITY_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import { instructionText } from '../scenarios';
import type { RecommendedAction } from '../types';

type Props = {
  action: RecommendedAction | null;
  noActionReason: string | null;
};

// Shared shell. Phase 2 renders family-specific detail inside it.
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
  const executableTone = action.executability === 'executable' ? 'chip-neutral' : 'chip-unknown';
  return (
    <section className="card card-action" aria-labelledby="action-heading">
      <h3 id="action-heading" className="card-kicker">
        {WORKSPACE_COPY.actionTitle}
        <span className="chip chip-neutral">{ACTION_FAMILY_LABEL[action.family]}</span>
        <span className={`chip ${executableTone}`}>{EXECUTABILITY_LABEL[action.executability]}</span>
      </h3>
      <p className="instruction">{instructionText(action)}</p>
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
    </section>
  );
}

export default RecommendedActionCard;

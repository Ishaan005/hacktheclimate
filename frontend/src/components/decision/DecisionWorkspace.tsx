import { SEARCH_COPY } from '../../decision/copy/search';
import { DECISION_COPY } from '../../decision/copy/workspace';
import { displayOverall } from '../../decision/rules';
import { isDemoSource } from '../../decision/source';
import { useDecisionWorkspace } from '../../decision/useDecisionWorkspace';
import StatusMessage from '../StatusMessage';
import ComparisonPanel from './ComparisonPanel';
import DecisionSummary from './DecisionSummary';
import EvidenceDrawer from './EvidenceDrawer';
import PlanPanel from './PlanPanel';
import SafetyPanel from './SafetyPanel';
import SituationSearch from './SituationSearch';
import TopBar from './TopBar';
import './DecisionWorkspace.css';

// Top bar → search → summary → safety (left) and plan (right) → comparison
// → evidence. Safety comes first on every row: the plan
// and its benefits are read against it. The screen shows a backend assessment and never sends an
// instruction.
function DecisionWorkspace() {
  const workspace = useDecisionWorkspace();
  const { state, stale, view, siteId, facts, edits, alternative } = workspace;
  const assessment = state.status === 'ready' ? { ...state.assessment, facts, edits, alternative } : null;
  const overall = assessment ? displayOverall(assessment, stale) : null;
  const demo = assessment ? isDemoSource(assessment.context.sourceKind) : false;

  let body = null;
  if (state.status === 'idle') {
    body = <StatusMessage tone="empty" title={DECISION_COPY.idleTitle} consequence={DECISION_COPY.idleConsequence} />;
  } else if (state.status === 'assessing') {
    body = <StatusMessage tone="loading" title={DECISION_COPY.assessingTitle} consequence={DECISION_COPY.assessingConsequence} />;
  } else if (state.status === 'unavailable') {
    body = <StatusMessage tone="unavailable" title={DECISION_COPY.unavailableTitle} consequence={DECISION_COPY.unavailableConsequence} detail={state.reason} />;
  } else if (state.status === 'error') {
    body = (
      <StatusMessage
        tone="error"
        title={DECISION_COPY.errorTitle}
        consequence={DECISION_COPY.errorConsequence}
        detail={state.reason}
        onRetry={workspace.rerun}
      />
    );
  } else if (assessment?.causeUnknown) {
    // Intake state, not a scenario: nothing is assessed until the cause is known.
    body = (
      <StatusMessage
        tone="unavailable"
        title={SEARCH_COPY.causeUnknownHeading}
        consequence={`${assessment.causeUnknown.reason} ${SEARCH_COPY.causeUnknownNext}`}
        items={assessment.causeUnknown.factsNeeded}
      />
    );
  } else if (assessment && overall) {
    const plan = alternative ?? assessment.proposed;
    // DesignersGuide order: binding condition, action and security first;
    // value next; evidence last, on expansion.
    body = (
      <>
        {/* Out of date is its own banner above the summary, said once. */}
        {stale && (
          <div className="decision-stale" role="status">
            <span>{DECISION_COPY.summaryStale}</span>
            <button type="button" className="button-primary" onClick={workspace.rerun}>{DECISION_COPY.rerun}</button>
          </div>
        )}
        <DecisionSummary assessment={assessment} overall={overall} plan={plan} stale={stale} demo={demo} />
        <div className="decision-panels">
          <div className="decision-panel decision-panel-safety">
            <SafetyPanel assessment={assessment} overall={overall} plan={plan} view={view} demo={demo} stale={stale} />
          </div>
          <div className="decision-panel decision-panel-plan">
            <PlanPanel
              assessment={assessment}
              alternative={alternative}
              stale={stale}
              demo={demo}
              onEditStep={workspace.editAlternativeStep}
              onSetAlternative={workspace.setAlternativePlan}
            />
          </div>
        </div>
        <ComparisonPanel outcomes={assessment.outcomes} benefits={assessment.benefits} view={view} demo={demo} />
        {!demo && <EvidenceDrawer evidence={assessment.evidence} edits={edits} validated={assessment.validated} sourceKind={assessment.context.sourceKind} />}
      </>
    );
  }

  return (
    <div className="decision-workspace">
      <TopBar
        context={assessment?.context ?? null}
        view={view}
        siteId={siteId}
        validated={assessment?.validated ?? false}
        onViewChange={workspace.changeView}
      />
      <SituationSearch onAssess={workspace.assess} busy={state.status === 'assessing'} />
      {body}
    </div>
  );
}

export default DecisionWorkspace;

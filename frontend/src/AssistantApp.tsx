import AssistantReplyCard from './components/AssistantReplyCard';
import CaseReview from './components/CaseReview';
import ClarificationForm from './components/ClarificationForm';
import DispatchDownResult from './components/DispatchDownResult';
import ScenarioWorkspace from './components/ScenarioWorkspace';
import SituationInput from './components/SituationInput';
import StatusMessage from './components/StatusMessage';
import { REVIEW_COPY, WORKSPACE_COPY } from './copy';
import { useSituationSolver } from './useSituationSolver';

// The operator describes the situation; the solver returns a scenario with
// its recommended action, the next-hour dispatch-down risk, or follow-up
// questions when the description is not enough.
function AssistantApp() {
  const { state, description, operatorCase, describe, evaluate, answer, correct, retry, cancel } = useSituationSolver();

  let result = null;
  if (state.status === 'intake') {
    result = <StatusMessage tone="loading" title={REVIEW_COPY.intakeTitle} consequence={REVIEW_COPY.intakeConsequence} />;
  } else if (state.status === 'reviewing' && operatorCase) {
    result = (
      <CaseReview
        operatorCase={operatorCase}
        extraction={state.extraction}
        onCorrect={correct}
        onEvaluate={evaluate}
        onCancel={cancel}
      />
    );
  } else if (state.status === 'solving') {
    result = <StatusMessage tone="loading" title={WORKSPACE_COPY.solvingTitle} consequence={WORKSPACE_COPY.solvingConsequence} />;
  } else if (state.status === 'clarifying') {
    // Key by round so each new set of questions starts with fresh answers.
    result = (
      <ClarificationForm
        key={state.round}
        clarification={state.clarification}
        description={description}
        round={state.round}
        onSubmit={answer}
        onCancel={cancel}
      />
    );
  } else if (state.status === 'stopped') {
    result = (
      <StatusMessage
        tone="unavailable"
        title={WORKSPACE_COPY.stoppedTitle}
        consequence={WORKSPACE_COPY.stoppedConsequence}
        items={state.missing}
        onRetry={cancel}
        retryLabel={WORKSPACE_COPY.clarifyCancel}
      />
    );
  } else if (state.status === 'solved') {
    // Key by content so a new answer resets any time the operator changed.
    const solved = state.result;
    if (solved.kind === 'scenario') {
      result = <ScenarioWorkspace key={solved.scenario.id} scenario={solved.scenario} />;
    } else if (solved.kind === 'assistant_reply') {
      result = (
        <>
          <AssistantReplyCard reply={solved.reply} />
          {solved.target && <DispatchDownResult key={solved.target} target={solved.target} />}
        </>
      );
    } else {
      result = <DispatchDownResult key={solved.target} target={solved.target} />;
    }
  } else if (state.status === 'no_match') {
    result = <StatusMessage tone="empty" title={WORKSPACE_COPY.noMatchTitle} consequence={WORKSPACE_COPY.noMatchConsequence} />;
  } else if (state.status === 'unavailable') {
    result = (
      <StatusMessage
        tone="unavailable"
        title={WORKSPACE_COPY.solverUnavailableTitle}
        consequence={WORKSPACE_COPY.solverUnavailableConsequence}
        detail={state.reason}
      />
    );
  } else if (state.status === 'error') {
    result = (
      <StatusMessage
        tone="error"
        title={WORKSPACE_COPY.solverErrorTitle}
        consequence={WORKSPACE_COPY.solverErrorConsequence}
        detail={state.reason}
        onRetry={retry}
      />
    );
  }

  return (
    <>
      <SituationInput onSubmit={(text) => describe(text)} />
      {result}
    </>
  );
}

export default AssistantApp;

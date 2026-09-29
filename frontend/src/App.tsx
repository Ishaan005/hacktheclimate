import AssistantReplyCard from './components/AssistantReplyCard';
import ClarificationForm from './components/ClarificationForm';
import DispatchDownResult from './components/DispatchDownResult';
import ScenarioWorkspace from './components/ScenarioWorkspace';
import SituationInput from './components/SituationInput';
import StatusMessage from './components/StatusMessage';
import { USE_FIXTURE } from './api';
import { COPY, WORKSPACE_COPY } from './copy';
import { useSituationSolver } from './useSituationSolver';
import './App.css';

// The operator describes the situation; the solver returns a scenario with
// its recommended action, the next-hour dispatch-down risk, or follow-up
// questions when the description is not enough.
function App() {
  const { state, description, describe, answer, retry, cancel } = useSituationSolver();

  let result = null;
  if (state.status === 'solving') {
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
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <span className="masthead-title">{COPY.teamName}</span>
          <span className="masthead-org">{COPY.eventName}</span>
        </div>
      </header>
      <div className="phase-banner">
        <p className="phase-inner">
          <span className="phase-tag">{COPY.appPhase}</span>
          <span>{USE_FIXTURE ? COPY.fixtureBanner : WORKSPACE_COPY.advisoryNote}</span>
        </p>
      </div>
      <main className="app-main">
        <h1 className="page-title">{COPY.appTitle}</h1>
        <SituationInput onSubmit={describe} />
        {result}
      </main>
    </div>
  );
}

export default App;

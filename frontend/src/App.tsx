import { useEffect, useRef, useState } from 'react';
import ScenarioWorkspace from './components/ScenarioWorkspace';
import SituationInput from './components/SituationInput';
import StatusMessage from './components/StatusMessage';
import { solveSituation, SolverUnavailableError, USE_FIXTURE } from './api';
import { COPY, WORKSPACE_COPY } from './copy';
import type { WorkspaceScenario } from './types';
import './App.css';

type SolveState =
  | { status: 'idle' }
  | { status: 'solving' }
  | { status: 'solved'; scenario: WorkspaceScenario }
  | { status: 'no_match' }
  | { status: 'unavailable'; reason: string }
  | { status: 'error'; reason: string };

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error';
}

// The operator describes the situation; the solver returns one scenario with
// its recommended action.
function App() {
  const [state, setState] = useState<SolveState>({ status: 'idle' });
  const [lastDescription, setLastDescription] = useState('');
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  function describeSituation(description: string) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLastDescription(description);
    setState({ status: 'solving' });
    solveSituation(description, controller.signal)
      .then((scenario) => {
        if (controller.signal.aborted) return;
        setState(scenario ? { status: 'solved', scenario } : { status: 'no_match' });
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof SolverUnavailableError) {
          setState({ status: 'unavailable', reason: err.message });
          return;
        }
        console.error('Error solving situation:', err);
        setState({ status: 'error', reason: errorMessage(err) });
      });
  }

  let result = null;
  if (state.status === 'solving') {
    result = <StatusMessage tone="loading" title={WORKSPACE_COPY.solvingTitle} consequence={WORKSPACE_COPY.solvingConsequence} />;
  } else if (state.status === 'solved') {
    result = <ScenarioWorkspace scenario={state.scenario} />;
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
        onRetry={() => describeSituation(lastDescription)}
      />
    );
  }

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <span className="masthead-title">Team Blue</span>
          <span className="masthead-org">Hack the Climate 2026</span>
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
        <SituationInput onSubmit={describeSituation} />
        {result}
      </main>
    </div>
  );
}

export default App;

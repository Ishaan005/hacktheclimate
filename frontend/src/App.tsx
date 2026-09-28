import { useState } from 'react';
import DispatchDownCard from './components/DispatchDownCard';
import DispatchDownChart from './components/DispatchDownChart';
import { COPY } from './copy';
import { DEFAULT_TARGET } from './dispatchDown';
import './App.css';

function App() {
  const [ddTarget, setDdTarget] = useState(DEFAULT_TARGET);

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
          <span>Historical one-hour-ahead replay of national dispatch-down risk, January 2026.</span>
        </p>
      </div>
      <main className="app-main">
        <h1 className="page-title">{COPY.appTitle}</h1>
        <DispatchDownCard onTargetChange={setDdTarget} />
        <DispatchDownChart target={ddTarget} />
      </main>
    </div>
  );
}

export default App;

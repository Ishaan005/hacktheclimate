import { useState } from 'react';
import AssistantApp from './AssistantApp';
import DecisionWorkspace from './components/decision/DecisionWorkspace';
import { USE_FIXTURE } from './api';
import { COPY, WORKSPACE_COPY } from './copy';
import { DECISION_COPY } from './decision/copy/workspace';
import './App.css';

type Page = 'decision' | 'assistant';

function bannerText(page: Page): string {
  if (page === 'assistant') return USE_FIXTURE ? COPY.fixtureBanner : WORKSPACE_COPY.advisoryNote;
  return USE_FIXTURE ? DECISION_COPY.fixtureNote : DECISION_COPY.advisoryNote;
}

// The decision workspace is the main screen. The earlier grid assistant
// (chat and dispatch-down replay) stays one tab away.
function App() {
  const [page, setPage] = useState<Page>('decision');
  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <img className="masthead-logo" src="/BREEZY.svg" alt="Breezy" width="88" height="18" />
          <span className="masthead-org">{COPY.eventName}</span>
          <nav className="masthead-nav" aria-label={DECISION_COPY.navLabel}>
            {(['decision', 'assistant'] as const).map((item) => (
              <button
                key={item}
                type="button"
                className="masthead-tab"
                aria-current={page === item ? 'page' : undefined}
                onClick={() => setPage(item)}
              >
                {item === 'decision' ? DECISION_COPY.navDecision : DECISION_COPY.navAssistant}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <div className="phase-banner">
        <p className="phase-inner">
          <span className="phase-tag">{COPY.appPhase}</span>
          <span>{bannerText(page)}</span>
        </p>
      </div>
      <main className={`app-main${page === 'decision' ? ' app-main-wide' : ''}`}>
        <h1 className="page-title">{page === 'decision' ? DECISION_COPY.title : COPY.appTitle}</h1>
        {page === 'decision' ? <DecisionWorkspace /> : <AssistantApp />}
      </main>
    </div>
  );
}

export default App;

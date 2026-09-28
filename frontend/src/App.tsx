import { useEffect, useState } from 'react';
import ForecastPanel from './components/ForecastPanel';
import ScenarioPanel from './components/ScenarioPanel';
import SummaryStrip from './components/SummaryStrip';
import { fetchOperatorView, fetchReviewedOutages, USE_FIXTURE } from './api';
import { COPY } from './copy';
import type { OperatorView, ReviewedOutageOption } from './types';
import './App.css';

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error';
}

function App() {
  const [outages, setOutages] = useState<ReviewedOutageOption[]>([]);
  const [selectedOutageId, setSelectedOutageId] = useState<string | null>(null);
  const [view, setView] = useState<OperatorView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchReviewedOutages(controller.signal)
      .then(setOutages)
      .catch((err) => {
        if (!controller.signal.aborted) console.error('Error loading reviewed outages:', err);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchOperatorView(selectedOutageId, controller.signal)
      .then(setView)
      .catch((err) => {
        if (controller.signal.aborted) return;
        console.error('Error loading operator view:', err);
        setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [selectedOutageId, reloadKey]);

  function selectOutage(outageId: string | null) {
    setSelectedOutageId(outageId);
    setLoading(true);
    setError(null);
  }

  function retry() {
    setLoading(true);
    setError(null);
    setReloadKey((key) => key + 1);
  }

  const selectedOutage = outages.find((item) => item.outage_id === selectedOutageId) ?? null;

  // Keep the last forecast on screen while only the scenario reloads.
  const forecastLoading = loading && !view;

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
          <span>{USE_FIXTURE ? COPY.fixtureBanner : 'Data from the combined forecast and scenario API.'}</span>
        </p>
      </div>
      <main className="app-main">
        <h1 className="page-title">{COPY.appTitle}</h1>
        <SummaryStrip view={view} loading={loading} selectedOutage={selectedOutage} />
        <div className="app-grid">
          <ForecastPanel
            forecast={view?.forecast ?? null}
            loading={forecastLoading}
            error={view ? null : error}
            onRetry={retry}
          />
          <ScenarioPanel
            outages={outages}
            selectedOutageId={selectedOutageId}
            onSelectOutage={selectOutage}
            scenario={view?.scenario ?? null}
            loading={loading}
            error={error}
            onRetry={retry}
          />
        </div>
      </main>
    </div>
  );
}

export default App;

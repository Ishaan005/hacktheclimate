import { useEffect, useState, type FormEvent } from 'react';
import StatusMessage from './StatusMessage';
import { DEFAULT_TARGET, MAX_TARGET, MIN_TARGET, fetchDispatchDown, validateTarget, type DispatchDownForecast } from '../dispatchDown';
import './DispatchDownCard.css';

const RISK_LABEL: Record<string, string> = { low: 'Low risk', medium: 'Medium risk', high: 'High risk' };

function formatTime(value: string): string {
  const date = new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('en-IE', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
  }) + ' UTC';
}

function modeLabel(mode: string): string {
  return mode === 'historical_replay' ? 'Historical replay' : mode.replace(/_/g, ' ');
}

function DispatchDownCard() {
  const [target, setTarget] = useState(DEFAULT_TARGET);
  const [draft, setDraft] = useState(DEFAULT_TARGET);
  const [inputError, setInputError] = useState<string | null>(null);
  const [data, setData] = useState<DispatchDownForecast | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchDispatchDown(target, controller.signal)
      .then((result) => { setData(result); setError(null); })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [target, reloadKey]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = validateTarget(draft);
    setInputError(problem);
    if (problem) return;
    setLoading(true);
    setError(null);
    if (draft === target) setReloadKey((k) => k + 1);
    else setTarget(draft);
  }

  const risk = (data?.risk ?? 'unknown').toLowerCase();
  const pct = data ? Math.round(data.event_probability * 1000) / 10 : 0;

  return (
    <section className="dd-card" aria-labelledby="dd-heading">
      <header className="dd-header">
        <div>
          <p className="dd-kind">National dispatch-down forecast</p>
          <h2 id="dd-heading">Next-hour dispatch-down risk</h2>
        </div>
        <form className="dd-form" onSubmit={submit} noValidate>
          <label className="dd-picker">
            <span>Forecast time (UTC)</span>
            <input
              type="datetime-local"
              step={1800}
              min={MIN_TARGET}
              max={MAX_TARGET}
              value={draft}
              aria-invalid={inputError ? true : undefined}
              aria-describedby="dd-hint"
              onChange={(e) => setDraft(e.target.value)}
            />
          </label>
          <button type="submit" className="dd-submit" disabled={loading}>
            {loading ? 'Loading…' : 'Get forecast'}
          </button>
          <p id="dd-hint" className={inputError ? 'dd-hint dd-hint-error' : 'dd-hint'} role={inputError ? 'alert' : undefined}>
            {inputError ?? 'Replay data covers 1–31 Jan 2026, every 30 minutes.'}
          </p>
        </form>
      </header>

      {error && !data ? (
        <StatusMessage
          tone="error"
          title="Dispatch-down forecast unavailable"
          consequence="No risk estimate is shown for this hour."
          detail={error}
          onRetry={() => { setLoading(true); setReloadKey((k) => k + 1); }}
        />
      ) : !data ? (
        <StatusMessage tone="loading" title="Loading forecast" consequence="Fetching the one-hour-ahead estimate." />
      ) : (
        <div className={`dd-body${loading ? ' dd-busy' : ''}`} aria-busy={loading}>
          {error && <p className="dd-inline-error" role="alert">Could not update: {error}. Showing previous result.</p>}
          <div className={`dd-risk dd-risk-${risk}`}>
            <span className="dd-risk-label">{RISK_LABEL[risk] ?? data.risk}</span>
            <span className="dd-risk-sub">for {formatTime(data.target_timestamp)}</span>
          </div>

          <div className="dd-metrics">
            <div className="dd-metric">
              <p className="dd-metric-label">Chance of dispatch-down</p>
              <p className="dd-metric-value">{pct.toFixed(1)}%</p>
              <div
                className="dd-bar"
                role="meter"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={pct}
                aria-label="Event probability"
              >
                <span className={`dd-bar-fill dd-risk-${risk}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
            <div className="dd-metric">
              <p className="dd-metric-label">Expected dispatch-down</p>
              <p className="dd-metric-value">
                {data.expected_dispatch_down_mwh.toFixed(1)} <span className="dd-unit">MWh</span>
              </p>
              <p className="dd-metric-note">National total over the hour</p>
            </div>
          </div>

          <dl className="dd-meta">
            <div><dt>Mode</dt><dd><span className="dd-tag">{modeLabel(data.mode)}</span></dd></div>
            <div><dt>Inputs as of</dt><dd>{formatTime(data.input_timestamp)}</dd></div>
            <div><dt>Forecast for</dt><dd>{formatTime(data.target_timestamp)}</dd></div>
            <div><dt>Horizon</dt><dd>{data.horizon_hours} hour{data.horizon_hours === 1 ? '' : 's'} ahead</dd></div>
          </dl>

          {data.limitations.length > 0 && (
            <div className="dd-limits">
              <p className="dd-limits-title">Limits</p>
              <ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default DispatchDownCard;

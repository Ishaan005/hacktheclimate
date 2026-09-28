import { useEffect, useState, type FormEvent } from 'react';
import { WORKSPACE_COPY } from '../copy';
import { formatDayTime } from '../format';
import { DEFAULT_TARGET, MAX_TARGET, MIN_TARGET, fetchDispatchDown, validateTarget, type DispatchDownForecast } from '../dispatchDown';
import StatusMessage from './StatusMessage';
import './DispatchDown.css';

const RISK_LABEL: Record<string, string> = { low: 'Low risk', elevated: 'Elevated risk', medium: 'Elevated risk', high: 'High risk' };

function modeLabel(mode: string): string {
  return mode === 'historical_replay' ? 'Historical replay' : mode.replace(/_/g, ' ');
}

type DispatchDownCardProps = {
  initialTarget?: string;
  onTargetChange?: (target: string) => void;
};

// Risk level is a model band, not a guardrail state, so it stays neutral:
// green, red and amber are reserved for guardrail status.
function DispatchDownCard({ initialTarget = DEFAULT_TARGET, onTargetChange }: DispatchDownCardProps) {
  const [target, setTarget] = useState(initialTarget);
  const [draft, setDraft] = useState(initialTarget);
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
        console.error('Error loading dispatch-down forecast:', err);
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
    onTargetChange?.(draft);
  }

  const risk = (data?.risk ?? 'unknown').toLowerCase();
  const pct = data ? Math.round(data.event_probability * 1000) / 10 : 0;

  return (
    <section className="card dd-card" aria-labelledby="dd-heading">
      <header className="dd-header">
        <div>
          <p className="card-kicker">
            National dispatch-down forecast
            {data && <span className="chip">{modeLabel(data.mode)}</span>}
          </p>
          <h2 id="dd-heading">Next-hour dispatch-down risk</h2>
        </div>
        <form className="dd-form" onSubmit={submit} noValidate>
          <label className="field">
            <span className="field-label">Forecast time (UTC)</span>
            <input
              className="input mono"
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
          <button type="submit" className="button-secondary" disabled={loading}>
            {loading ? 'Loading…' : 'Get forecast'}
          </button>
          <p id="dd-hint" className={inputError ? 'field-hint field-hint-error' : 'field-hint'} role={inputError ? 'alert' : undefined}>
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
          {error && <p className="field-hint field-hint-error" role="alert">Could not update: {error}. Showing previous result.</p>}
          <p className="card-headline">
            {RISK_LABEL[risk] ?? data.risk}
            <span className="dd-headline-time mono">for {formatDayTime(data.target_timestamp)}</span>
          </p>

          <dl className="metrics">
            <div className="metric">
              <dt className="metric-label">Chance of dispatch-down</dt>
              <dd className="metric-value">{pct.toFixed(1)}%</dd>
              <dd>
                <span className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Event probability">
                  <span className="meter-fill" style={{ width: `${pct}%` }} />
                </span>
              </dd>
            </div>
            <div className="metric">
              <dt className="metric-label">Expected dispatch-down</dt>
              <dd className="metric-value">{data.expected_dispatch_down_mwh.toFixed(1)} MWh</dd>
              <dd className="metric-detail">National total over the hour</dd>
            </div>
          </dl>

          <dl className="fields">
            <div><dt>Inputs as of</dt><dd className="mono">{formatDayTime(data.input_timestamp)}</dd></div>
            <div><dt>Forecast for</dt><dd className="mono">{formatDayTime(data.target_timestamp)}</dd></div>
            <div><dt>Horizon</dt><dd>{data.horizon_hours} hour{data.horizon_hours === 1 ? '' : 's'} ahead</dd></div>
            <div><dt>Time zone</dt><dd>{WORKSPACE_COPY.timeZoneNote}</dd></div>
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

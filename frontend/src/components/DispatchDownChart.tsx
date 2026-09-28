import { useEffect, useState } from 'react';
import StatusMessage from './StatusMessage';
import { fetchDispatchDownDay, type DispatchDownDay } from '../dispatchDown';
import './DispatchDown.css';

const W = 760;
const H = 300;
const PAD = { top: 32, right: 56, bottom: 36, left: 48 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

function niceMax(value: number): number {
  if (value <= 0) return 10;
  const step = 10 ** Math.floor(Math.log10(value));
  return Math.ceil(value / step) * step;
}

function timeOf(ts: string): string {
  return ts.slice(11, 16);
}

function formatDate(date: string): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString('en-IE', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  });
}

type Props = { target: string };

function DispatchDownChart({ target }: Props) {
  const [day, setDay] = useState<DispatchDownDay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchDispatchDownDay(target, controller.signal)
      .then((result) => { setDay(result); setError(null); })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Unknown error');
      });
    return () => controller.abort();
  }, [target, reloadKey]);

  const points = day?.points ?? [];
  const n = points.length;
  const maxMwh = niceMax(Math.max(0, ...points.map((p) => p.expected_dispatch_down_mwh)));
  const slot = n ? PLOT_W / n : 0;
  const x = (i: number) => PAD.left + slot * (i + 0.5);
  const yP = (p: number) => PAD.top + PLOT_H * (1 - p);
  const yM = (m: number) => PAD.top + PLOT_H * (1 - m / maxMwh);
  const selected = points.findIndex((p) => timeOf(p.target_timestamp) === target.slice(11, 16));
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${yP(p.event_probability).toFixed(1)}`).join(' ');
  const active = hover ?? (selected >= 0 ? selected : null);
  const activePoint = active !== null ? points[active] : null;
  const totalMwh = points.reduce((sum, p) => sum + p.expected_dispatch_down_mwh, 0);
  const peak = points.reduce<number>((best, p, i) => (p.event_probability > (points[best]?.event_probability ?? -1) ? i : best), 0);

  return (
    <section className="card dd-card" aria-labelledby="ddc-heading">
      <header className="dd-header">
        <div>
          <p className="card-kicker">Replay across the day</p>
          <h2 id="ddc-heading">Dispatch-down risk through {day ? formatDate(day.date) : 'the day'}</h2>
        </div>
        <ul className="ddc-legend" aria-label="Legend">
          <li><span className="ddc-key ddc-key-line" aria-hidden="true" />Chance of dispatch-down (left axis)</li>
          <li><span className="ddc-key ddc-key-bar" aria-hidden="true" />Expected MWh (right axis)</li>
        </ul>
      </header>

      {error && !day ? (
        <StatusMessage tone="error" title="Chart unavailable" consequence="The day view could not be loaded." detail={error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : !day ? (
        <StatusMessage tone="loading" title="Loading chart" consequence="Fetching every half-hour for this day." />
      ) : (
        <>
          <div className="ddc-readout" aria-live="polite">
            {activePoint ? (
              <>
                <strong className="mono">{timeOf(activePoint.target_timestamp)}</strong>
                <span>{(activePoint.event_probability * 100).toFixed(1)}% chance</span>
                <span>{activePoint.expected_dispatch_down_mwh.toFixed(1)} MWh expected</span>
                {active === selected && hover === null && <span className="chip chip-advisory">Selected time</span>}
              </>
            ) : <span>Hover the chart to inspect a half-hour.</span>}
          </div>
          <svg
            className="ddc-svg"
            viewBox={`0 0 ${W} ${H}`}
            role="img"
            aria-label={`Half-hourly dispatch-down chance and expected MWh for ${day.date}`}
            onMouseLeave={() => setHover(null)}
          >
            {[0, 0.25, 0.5, 0.75, 1].map((t) => (
              <g key={t}>
                <line className="ddc-grid" x1={PAD.left} x2={W - PAD.right} y1={yP(t)} y2={yP(t)} />
                <text className="ddc-axis" x={PAD.left - 8} y={yP(t) + 4} textAnchor="end">{t * 100}%</text>
                <text className="ddc-axis" x={W - PAD.right + 8} y={yP(t) + 4}>{Math.round(maxMwh * t)}</text>
              </g>
            ))}
            <text className="ddc-axis" x={W - PAD.right + 8} y={PAD.top - 16}>MWh</text>

            {points.map((p, i) => (
              <rect
                key={p.target_timestamp}
                className={i === active ? 'ddc-bar ddc-bar-active' : 'ddc-bar'}
                x={x(i) - slot * 0.35}
                width={slot * 0.7}
                y={yM(p.expected_dispatch_down_mwh)}
                height={Math.max(0, PAD.top + PLOT_H - yM(p.expected_dispatch_down_mwh))}
              />
            ))}
            <line className="ddc-threshold" x1={PAD.left} x2={W - PAD.right} y1={yP(0.7)} y2={yP(0.7)} />
            <line className="ddc-threshold" x1={PAD.left} x2={W - PAD.right} y1={yP(0.3)} y2={yP(0.3)} />
            <path className="ddc-line" d={line} />
            {selected >= 0 && <line className="ddc-selected" x1={x(selected)} x2={x(selected)} y1={PAD.top} y2={PAD.top + PLOT_H} />}
            {activePoint && active !== null && (
              <circle className="ddc-dot" cx={x(active)} cy={yP(activePoint.event_probability)} r={5} />
            )}
            {/* Band labels last, with a halo, so bars and the line never cover them. */}
            <text className="ddc-threshold-label" x={PAD.left + 6} y={yP(0.7) - 6}>High (70%)</text>
            <text className="ddc-threshold-label" x={PAD.left + 6} y={yP(0.3) - 6}>Elevated (30%)</text>
            {points.map((p, i) => (i % 6 === 0 ? (
              <text key={`t${i}`} className="ddc-axis" x={x(i)} y={H - PAD.bottom + 18} textAnchor="middle">{timeOf(p.target_timestamp)}</text>
            ) : null))}
            <text className="ddc-axis" x={PAD.left + PLOT_W / 2} y={H - 4} textAnchor="middle">Forecast time (UTC)</text>
            {points.map((_, i) => (
              <rect
                key={`h${i}`}
                className="ddc-hit"
                x={x(i) - slot / 2}
                width={slot}
                y={PAD.top}
                height={PLOT_H}
                onMouseEnter={() => setHover(i)}
              />
            ))}
          </svg>
          <dl className="fields">
            <div><dt>Peak chance</dt><dd>{(points[peak].event_probability * 100).toFixed(1)}% at {timeOf(points[peak].target_timestamp)}</dd></div>
            <div><dt>Expected total for the day</dt><dd>{totalMwh.toFixed(0)} MWh</dd></div>
            <div><dt>Half-hours at high risk</dt><dd>{points.filter((p) => p.event_probability >= 0.7).length} of {n}</dd></div>
          </dl>
          <p className="ddc-note">Each point is a separate one-hour-ahead historical replay. Expected MWh is chance × predicted volume, national total. All times UTC.</p>
        </>
      )}
    </section>
  );
}

export default DispatchDownChart;

import { WORKSPACE_COPY } from '../copy';
import type { BindingCondition } from '../types';
import StatusChip from './StatusChip';

// Loading metrics read like "Line W-1 loading 104% of rating". Other metrics
// (voltage, SNSP, inertia) have no 100% limit, so they get no meter.
function loadingPct(metric: string): number | null {
  const match = metric.match(/(\d+(?:\.\d+)?)%\s+of rating/i);
  return match ? Number(match[1]) : null;
}

const METER_MAX = 125;

function LoadingMeter({ value }: { value: number }) {
  const width = `${(Math.min(value, METER_MAX) / METER_MAX) * 100}%`;
  return (
    <div className="loading-meter" aria-hidden="true">
      <span className="loading-meter-track">
        <span className={`loading-meter-fill${value > 100 ? ' loading-meter-over' : ''}`} style={{ width }} />
        <span className="loading-meter-limit" style={{ left: `${(100 / METER_MAX) * 100}%` }} />
      </span>
      <span className="loading-meter-scale">
        <span>Loading <span className="mono">{value}%</span></span>
        <span>Rating <span className="mono">100%</span></span>
      </span>
    </div>
  );
}

function BindingConditionCard({ binding }: { binding: BindingCondition | null }) {
  const loading = binding ? loadingPct(binding.metric) : null;
  return (
    <section className={`card card-binding card-binding-${binding?.status ?? 'unknown'}`} aria-labelledby="binding-heading">
      <h3 id="binding-heading" className="card-kicker">{WORKSPACE_COPY.bindingTitle}</h3>
      {binding ? (
        <>
          <p className="card-headline">
            {binding.type} <StatusChip status={binding.status} prefix="Binding status" />
          </p>
          {loading !== null && <LoadingMeter value={loading} />}
          <p className={`binding-margin binding-margin-${binding.status}`}>
            <span className="binding-margin-label">Margin to limit</span>
            <span className="binding-margin-value">{binding.margin ?? 'Unknown'}</span>
          </p>
          <dl className="fields">
            <div><dt>Limiting metric</dt><dd>{binding.metric}</dd></div>
            <div><dt>Location</dt><dd>{binding.location ?? 'Unknown'}</dd></div>
          </dl>
        </>
      ) : (
        <p className="card-headline">{WORKSPACE_COPY.bindingNone}</p>
      )}
    </section>
  );
}

export default BindingConditionCard;

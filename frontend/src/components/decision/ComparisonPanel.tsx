import { COLUMN_LABEL, COMPARISON_COPY } from '../../decision/copy/comparison';
import { comparisonEnergy } from '../../decision/impact';
import { outcomeFor } from '../../decision/rules';
import type { Benefits, Established, OutcomeState, ScenarioFamily, ViewMode } from '../../decision/types';
import { formatNumber, formatWindow } from '../../format';
import ImpactCalculator from './ImpactCalculator';
import './ComparisonPanel.css';

type Props = {
  outcomes: OutcomeState[];
  benefits: Benefits;
  view: ViewMode;
  demo?: boolean;
  families?: ScenarioFamily[];
};

function value(metric: Established): string {
  return metric.value === null ? '—' : formatNumber(metric.value, metric.unit);
}

function DispatchDownChart({ outcomes, family }: { outcomes: OutcomeState[]; family: ScenarioFamily }) {
  const before = outcomeFor(outcomes, 'no_new_instruction');
  const after = outcomeFor(outcomes, 'proposed');
  const key = family === 'transmission' ? 'constrainedMwh' : 'curtailedMwh';
  const beforeMwh = before?.available ? before[key].value : null;
  const afterMwh = after?.available ? after[key].value : null;
  const comparable = before && after && before.windowStart === after.windowStart && before.windowEnd === after.windowEnd
    && before.includesActiveInstructions && after.includesActiveInstructions;
  const valid = comparable && beforeMwh !== null && beforeMwh !== undefined && afterMwh !== null && afterMwh !== undefined
    && Number.isFinite(beforeMwh) && Number.isFinite(afterMwh) && beforeMwh >= 0 && afterMwh >= 0;

  if (!valid) return <p className="comparison-unavailable">Comparable dispatch-down energy is unavailable for this case.</p>;

  const maximum = Math.max(beforeMwh, afterMwh, 1);
  const saving = comparisonEnergy(outcomes, family);
  const difference = beforeMwh - afterMwh;
  const headline = difference > 0
    ? `${formatNumber(difference, 'MWh')} ${saving !== null && after?.safety === 'pass' ? 'avoided dispatch-down' : 'potential avoided dispatch-down'}`
    : difference < 0
      ? `${formatNumber(Math.abs(difference), 'MWh')} higher dispatch-down`
      : 'No change in dispatch-down';

  return (
    <figure className="comparison-chart" aria-label={`${headline}. No input ${beforeMwh} MWh; proposed plan ${afterMwh} MWh.`}>
      <figcaption>
        <span className="comparison-chart-eyebrow">{family === 'transmission' ? 'Constrained energy' : 'Curtailed energy'}</span>
        <strong>{headline}</strong>
      </figcaption>
      <div className="comparison-bars">
        {([['no_new_instruction', beforeMwh], ['proposed', afterMwh]] as const).map(([column, amount]) => (
          <div className="comparison-bar-item" key={column}>
            <strong>{formatNumber(amount, 'MWh')}</strong>
            <div className="comparison-bar-track"><span className={`comparison-bar comparison-bar-${column}`} style={{ height: `${Math.max(6, amount / maximum * 100)}%` }} /></div>
            <span>{COLUMN_LABEL[column]}</span>
          </div>
        ))}
      </div>
    </figure>
  );
}

function ComparisonPanel({ outcomes, families = [] }: Props) {
  const before = outcomeFor(outcomes, 'no_new_instruction');
  const after = outcomeFor(outcomes, 'proposed');
  const family = families[0] ?? 'transmission';
  const sameWindow = before && after && before.windowStart === after.windowStart && before.windowEnd === after.windowEnd;
  const rows = [
    ['Safety result', before?.safety ?? '—', after?.safety ?? '—'],
    ['Worst limit margin', before?.worstMargin ?? '—', after?.worstMargin ?? '—'],
    ['Delivered relief', before ? value(before.deliveredReliefMw) : '—', after ? value(after.deliveredReliefMw) : '—'],
    ['Response time', before ? value(before.responseTimeMinutes) : '—', after ? value(after.responseTimeMinutes) : '—'],
    ['Time to breach', before ? value(before.timeToBreachMinutes) : '—', after ? value(after.timeToBreachMinutes) : '—'],
  ];

  return (
    <section className="card comparison-panel" aria-labelledby="comparison-heading">
      <div className="panel-header">
        <h2 id="comparison-heading" className="panel-title">{COMPARISON_COPY.title}</h2>
        {before?.available && <span className="panel-meta comparison-window">{formatWindow(before.windowStart, before.windowEnd)}</span>}
      </div>
      {!sameWindow && <p className="comparison-warning" role="alert">The two outcomes use different time windows and cannot be compared.</p>}
      <DispatchDownChart outcomes={outcomes} family={family} />
      <ImpactCalculator outcomes={outcomes} families={families} />
      <details className="comparison-details">
        <summary>Safety and response details</summary>
        <div className="table-scroll"><table className="comparison-table">
          <thead><tr><th scope="col">Measure</th><th scope="col">No input</th><th scope="col">Proposed plan</th></tr></thead>
          <tbody>{rows.map(([label, first, second]) => <tr key={label}>
            <th scope="row">{label}</th><td>{first}</td><td>{second}</td>
          </tr>)}</tbody>
        </table></div>
      </details>
    </section>
  );
}

export default ComparisonPanel;

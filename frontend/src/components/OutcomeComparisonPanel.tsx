import { WORKSPACE_COPY } from '../copy';
import { formatEur, formatNumber, formatPercent } from '../format';
import { avoidedWasteMwh, dispatchDownReductionPct } from '../scenarios';
import type { OutcomeState, WorkspaceScenario } from '../types';
import MetricCard from './MetricCard';
import StatusChip from './StatusChip';

function heightPct(value: number | null, max: number): string {
  return value === null || max <= 0 ? '0%' : `${(value / max) * 100}%`;
}

type ColumnProps = {
  title: string;
  state: OutcomeState | null;
  max: number;
  // Post-action column: the waste avoided against baseline, drawn as a pale
  // segment stacked above the remaining waste.
  avoided?: number | null;
};

function OutcomeColumn({ title, state, max, avoided }: ColumnProps) {
  const waste = state?.dispatchDownWasteMwh ?? null;
  return (
    <li className={avoided === undefined ? 'outcome-column outcome-column-baseline' : 'outcome-column outcome-column-post'}>
      <span className="outcome-value num">{formatNumber(waste, 'MWh')}</span>
      <span className="outcome-bar" aria-hidden="true">
        {avoided != null && avoided > 0 && (
          <span
            className="outcome-bar-avoided"
            style={{ height: heightPct(avoided, max) }}
            title={`${formatNumber(avoided, 'MWh')} avoided`}
          />
        )}
        <span
          className="outcome-bar-fill"
          style={{ height: heightPct(waste, max) }}
          title={`${title}: ${formatNumber(waste, 'MWh')}`}
        />
      </span>
      <span className="outcome-column-label">{title}</span>
      <StatusChip status={state?.securityResult ?? 'unknown'} prefix={`${title} security result`} />
    </li>
  );
}

// Baseline and post-action stand side by side on one vertical scale so the
// bar heights compare directly. Each column shows its security result under
// the bar.
function OutcomeComparisonPanel({ scenario }: { scenario: WorkspaceScenario }) {
  const reduction = dispatchDownReductionPct(scenario);
  const avoided = avoidedWasteMwh(scenario);
  const max = Math.max(scenario.baseline.dispatchDownWasteMwh ?? 0, scenario.postAction?.dispatchDownWasteMwh ?? 0);
  return (
    <section className="card card-outcome" aria-labelledby="outcome-heading">
      <h3 id="outcome-heading" className="card-kicker">{WORKSPACE_COPY.outcomeTitle}</h3>
      <div className="outcome-body">
        <figure className="outcome-chart">
          <figcaption className="outcome-chart-caption">Dispatch-down waste</figcaption>
          {avoided != null && avoided > 0 && (
            <ul className="outcome-legend">
              <li><span className="outcome-swatch outcome-swatch-fill" aria-hidden="true" />Remaining</li>
              <li><span className="outcome-swatch outcome-swatch-avoided" aria-hidden="true" />Avoided</li>
            </ul>
          )}
          <ul className="outcome-columns">
            <OutcomeColumn title={WORKSPACE_COPY.baseline} state={scenario.baseline} max={max} />
            <OutcomeColumn title={WORKSPACE_COPY.postAction} state={scenario.postAction} max={max} avoided={avoided} />
          </ul>
        </figure>
        <dl className="metrics metrics-row" aria-label="Change from recommended action">
          <MetricCard label="Avoided dispatch-down waste" value={formatNumber(avoided, 'MWh')} />
          <MetricCard
            label="Dispatch-down reduction"
            value={reduction === 'n/a' ? 'N/A' : formatPercent(reduction)}
            detail={reduction === 'n/a' ? 'Baseline waste is zero.' : undefined}
          />
          <MetricCard label="Net financial value" value={formatEur(scenario.impact?.netFinancialValueEur ?? null)} />
          <MetricCard
            label="Estimated avoided emissions"
            value={formatNumber(scenario.impact?.estimatedAvoidedEmissionsTco2e ?? null, 'tCO2e', 1)}
            detail="Scenario estimate, not a verified carbon saving."
          />
          <MetricCard
            priority="secondary"
            label="Gross market opportunity"
            value={formatEur(scenario.impact?.grossMarketOpportunityEur ?? null)}
          />
        </dl>
      </div>
    </section>
  );
}

export default OutcomeComparisonPanel;

import { WORKSPACE_COPY } from '../copy';
import { formatEur, formatNumber, formatPercent } from '../format';
import { avoidedWasteMwh, dispatchDownReductionPct } from '../scenarios';
import type { OutcomeState, WorkspaceScenario } from '../types';
import MetricCard from './MetricCard';
import StatusChip from './StatusChip';

function widthPct(value: number | null, max: number): string {
  return value === null || max <= 0 ? '0%' : `${(value / max) * 100}%`;
}

type RowProps = {
  title: string;
  state: OutcomeState | null;
  max: number;
  // Post-action row: the waste avoided against baseline, drawn as a pale
  // segment after the remaining waste.
  avoided?: number | null;
};

function OutcomeRow({ title, state, max, avoided }: RowProps) {
  const waste = state?.dispatchDownWasteMwh ?? null;
  return (
    <tr className={avoided === undefined ? 'outcome-row-baseline' : 'outcome-row-post'}>
      <th scope="row">{title}</th>
      <td>
        <StatusChip status={state?.securityResult ?? 'unknown'} prefix={`${title} security result`} />
      </td>
      <td className="outcome-bar-cell" aria-hidden="true">
        <span className="outcome-bar">
          <span className="outcome-bar-fill" style={{ width: widthPct(waste, max) }} />
          {avoided != null && avoided > 0 && (
            <span
              className="outcome-bar-avoided"
              style={{ width: widthPct(avoided, max) }}
              title={`${formatNumber(avoided, 'MWh')} avoided`}
            />
          )}
        </span>
      </td>
      <td className="num">{formatNumber(waste, 'MWh')}</td>
    </tr>
  );
}

// Baseline and post-action share one row layout and one bar scale so they can
// be read down. Security comes before any value metric.
function OutcomeComparisonPanel({ scenario }: { scenario: WorkspaceScenario }) {
  const reduction = dispatchDownReductionPct(scenario);
  const avoided = avoidedWasteMwh(scenario);
  const max = Math.max(scenario.baseline.dispatchDownWasteMwh ?? 0, scenario.postAction?.dispatchDownWasteMwh ?? 0);
  return (
    <section className="card card-outcome" aria-labelledby="outcome-heading">
      <h3 id="outcome-heading" className="card-kicker">{WORKSPACE_COPY.outcomeTitle}</h3>
      <table className="outcome-table">
        <thead>
          <tr>
            <th scope="col"><span className="visually-hidden">State</span></th>
            <th scope="col">Security result</th>
            <th scope="col">Dispatch-down waste</th>
            <th scope="col" className="num"><span className="visually-hidden">MWh</span></th>
          </tr>
        </thead>
        <tbody>
          <OutcomeRow title={WORKSPACE_COPY.baseline} state={scenario.baseline} max={max} />
          <OutcomeRow title={WORKSPACE_COPY.postAction} state={scenario.postAction} max={max} avoided={avoided} />
        </tbody>
      </table>
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
    </section>
  );
}

export default OutcomeComparisonPanel;

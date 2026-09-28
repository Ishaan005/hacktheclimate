import { COPY, WORKSPACE_COPY } from '../copy';
import { formatEur, formatNumber, formatPercent, formatTime } from '../format';
import { avoidedWasteMwh, dispatchDownReductionPct } from '../scenarios';
import type { OutcomeState, WorkspaceScenario } from '../types';
import MetricCard from './MetricCard';
import StatusChip from './StatusChip';

function StateColumn({ title, state }: { title: string; state: OutcomeState | null }) {
  return (
    <div className="outcome-column">
      <h4>{title}</h4>
      <dl className="metrics">
        <MetricCard
          label="Security result"
          value={<StatusChip status={state?.securityResult ?? 'unknown'} prefix={`${title} security result`} />}
        />
        <MetricCard label="Dispatch-down waste" value={formatNumber(state?.dispatchDownWasteMwh ?? null, 'MWh')} />
      </dl>
    </div>
  );
}

// Baseline and post-action use identical labels and order so they can be
// read across. Security comes before any value metric.
function OutcomeComparisonPanel({ scenario }: { scenario: WorkspaceScenario }) {
  const reduction = dispatchDownReductionPct(scenario);
  const earliest = scenario.action?.earliestExecution;
  return (
    <section className="card card-outcome" aria-labelledby="outcome-heading">
      <h3 id="outcome-heading" className="card-kicker">{WORKSPACE_COPY.outcomeTitle}</h3>
      <div className="outcome-columns">
        <StateColumn title={WORKSPACE_COPY.baseline} state={scenario.baseline} />
        <StateColumn title={WORKSPACE_COPY.postAction} state={scenario.postAction} />
      </div>
      <dl className="metrics metrics-row" aria-label="Change from recommended action">
        <MetricCard label="Avoided dispatch-down waste" value={formatNumber(avoidedWasteMwh(scenario), 'MWh')} />
        <MetricCard
          label="Dispatch-down reduction"
          value={reduction === 'n/a' ? 'N/A' : formatPercent(reduction)}
          detail={reduction === 'n/a' ? 'Baseline waste is zero.' : undefined}
        />
        <MetricCard label="Net financial value" value={formatEur(scenario.impact?.netFinancialValueEur ?? null)} />
        <MetricCard label="Earliest achievable execution" value={earliest ? formatTime(earliest) : COPY.notAvailable} />
        <MetricCard
          priority="secondary"
          label="Gross market opportunity"
          value={formatEur(scenario.impact?.grossMarketOpportunityEur ?? null)}
        />
        <MetricCard
          priority="secondary"
          label="Estimated avoided emissions"
          value={formatNumber(scenario.impact?.estimatedAvoidedEmissionsTco2e ?? null, 'tCO2e', 1)}
          detail="Scenario estimate, not a verified carbon saving."
        />
      </dl>
    </section>
  );
}

export default OutcomeComparisonPanel;

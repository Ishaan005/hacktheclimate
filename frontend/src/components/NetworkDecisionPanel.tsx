import type { NetworkDecision, SafetyResult } from '../types';
import { formatDateTime } from '../format';
import Panel from './Panel';
import StatusMessage from './StatusMessage';

type Props = {
  decision: NetworkDecision | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
};

const CHECKS = ['thermal', 'islanding', 'snsp', 'voltage', 'inertia', 'rocof'] as const;

function SafetyChecks({ safety }: { safety: SafetyResult }) {
  return (
    <div className="block">
      <h3>Safety screen: {safety.overall}</h3>
      <ul>
        {CHECKS.map((name) => (
          <li key={name}>
            <strong>{name.toUpperCase()}: {safety[name].status}</strong> — {safety[name].reason}
          </li>
        ))}
      </ul>
    </div>
  );
}

function NetworkDecisionPanel({ decision, loading, error, onRetry }: Props) {
  let body;
  if (loading) {
    body = <StatusMessage tone="loading" title="Loading network screen…" consequence="Future network states and action checks are being calculated." />;
  } else if (error) {
    body = <StatusMessage tone="unavailable" title="Network screen is unavailable" consequence="The required point-in-time forecast or reviewed case inputs are missing." detail={error} onRetry={onRetry} />;
  } else if (!decision) {
    body = <StatusMessage tone="unavailable" title="No network screen yet" consequence="Supply the reviewed case and forecast inputs to evaluate future states." />;
  } else {
    const peak = decision.rows.reduce((best, row) =>
      row.expected_constraint_mwh > best.expected_constraint_mwh ? row : best,
    );
    body = (
      <>
        <div className="block">
          <h3>Highest expected national constraint half-hour</h3>
          <p>{formatDateTime(peak.valid_time)} · {peak.expected_constraint_mwh.toFixed(1)} MWh supplied upstream</p>
          <p>Planning-case scenario: {peak.network.scenario}. Highest modelled MW/MVA proxy: {peak.network.max_dc_loading_proxy_pct?.toFixed(1) ?? 'unknown'}%.</p>
          <p>Studied outage asset: <code>{decision.network.planned_outage.asset_id}</code>. Case date: {decision.network.case_scenario_date ?? 'unknown'}.</p>
        </div>
        <SafetyChecks safety={peak.network.safety} />
        <div className="block">
          <h3>Flexible actions</h3>
          {decision.actions.length ? (
            <ul>
              {decision.actions.map((action) => (
                <li key={action.action_id}>
                  <strong>{action.action_id}</strong>: {action.power_mw.toFixed(1)} MW · safety {action.safety_overall} · modelled capture upper bound {action.modeled_capture_upper_bound_mwh.toFixed(1)} MWh
                </li>
              ))}
            </ul>
          ) : <p>No reviewed flexible actions are loaded.</p>}
          <p><strong>Recommendation: none.</strong> {decision.health.recommendation_reason}</p>
        </div>
        <details className="disclosure">
          <summary>Missing evidence and provenance</summary>
          <p>Forecast source: {decision.health.forecast_source}; issued {formatDateTime(decision.health.forecast_issue_time)}.</p>
          <ul>{decision.health.missing_inputs.map((item) => <li key={item}>{item}</li>)}</ul>
        </details>
      </>
    );
  }
  return (
    <Panel
      kind="Planning model and action screen"
      variant="scenario"
      title="TYTFS network and safety screen"
      scope="48 future half-hours on a 2024 planning case, with reviewed action candidates when available"
      caveat="DC loading is a screening proxy. Unsupported safety checks stay UNKNOWN, and no action is recommended without complete safety and impact evidence."
    >
      {body}
    </Panel>
  );
}

export default NetworkDecisionPanel;

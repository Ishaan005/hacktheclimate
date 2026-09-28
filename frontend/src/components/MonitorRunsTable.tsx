import type { FlowDelta, RunName, ScenarioReport } from '../types';
import { formatNumber, formatPercent } from '../format';

const RUN_LABELS: Record<RunName, string> = {
  intact: 'Intact',
  planned_outage: 'Planned outage',
  selected_n_minus_one: 'Planned outage + selected N-1',
};

const RUN_ORDER: RunName[] = ['intact', 'planned_outage', 'selected_n_minus_one'];

function monitorDelta(deltas: FlowDelta[] | null, report: ScenarioReport): number | null {
  const match = deltas?.find(
    (item) => item.asset_type === report.monitored.asset_type && item.asset_id === report.monitored.asset_id,
  );
  return match?.delta_flow_mw ?? null;
}

function formatSigned(value: number | null): string {
  if (value === null) return formatNumber(null, 'MW');
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} MW`;
}

// On narrow screens CSS turns each row into a card; data-label supplies the
// column name for that layout.
function MonitorRunsTable({ report }: { report: ScenarioReport }) {
  const deltaFromIntact: Record<RunName, number | null> = {
    intact: null,
    planned_outage: monitorDelta(report.flow_deltas_from_intact.planned_outage, report),
    selected_n_minus_one: monitorDelta(report.flow_deltas_from_intact.selected_n_minus_one, report),
  };
  return (
    <div className="block runs-block">
      <h3>Modelled flow on monitored {report.monitored.asset_type}</h3>
      <p className="block-hint">
        <code>{report.monitored.asset_id}</code> · DC active-power flow in the planning case, by run
      </p>
      <table className="runs-table">
        <thead>
          <tr>
            <th scope="col">Run</th>
            <th scope="col">Solver</th>
            <th scope="col" className="num">Modelled flow</th>
            <th scope="col" className="num">Change vs intact</th>
            <th scope="col" className="num">DC loading proxy</th>
            <th scope="col" className="num">Headroom proxy</th>
          </tr>
        </thead>
        <tbody>
          {RUN_ORDER.map((name) => {
            const run = report.runs[name];
            const flow = report.monitor_by_run[name];
            return (
              <tr key={name}>
                <th scope="row" data-label="Run">{RUN_LABELS[name]}</th>
                <td data-label="Solver">
                  {run.status}
                  {run.reason && <span className="cell-note"> {run.reason}</span>}
                </td>
                <td className="num" data-label="Modelled flow">{formatNumber(flow?.flow_mw ?? null, 'MW', 1)}</td>
                <td className="num" data-label="Change vs intact">{name === 'intact' ? '—' : formatSigned(deltaFromIntact[name])}</td>
                <td className="num" data-label="DC loading proxy">{formatPercent(flow?.dc_loading_pct_proxy ?? null, 1)}</td>
                <td className="num" data-label="Headroom proxy">{formatNumber(flow?.dc_headroom_mw_unity_pf_proxy ?? null, 'MW')}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default MonitorRunsTable;

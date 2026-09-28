import type { ScenarioReport } from '../types';
import { GLOSSARY } from '../copy';
import { formatNumber, formatPercent } from '../format';
import { runViews, SEVERITY_TEXT, signed } from '../insights';
import type { RunView } from '../insights';
import Term from './Term';
import './MonitorRunsTable.css';

const SOLVER_TEXT: Record<RunView['status'], string> = {
  ok: 'Solved',
  islanded: 'Part of the network was cut off in this run; figures for that part are not reliable.',
  unsolved: 'The model could not solve this run, so no flow is shown.',
};

function Change({ value, unit, digits = 1 }: { value: number | null; unit: string; digits?: number }) {
  if (value === null) return null;
  return (
    <span className="change" aria-label={`${signed(value, unit, digits)} compared with all equipment in service`}>
      {signed(value, unit, digits)}
    </span>
  );
}

// On narrow panels CSS turns each row into a labelled block; data-label
// supplies the column name for that layout.
function MonitorRunsTable({ report }: { report: ScenarioReport }) {
  const views = runViews(report);
  const rating = report.monitor_by_run.intact?.rating_mva ?? null;
  return (
    <div className="block runs-block">
      <h3>Modelled effect on the monitored branch</h3>
      <p className="block-hint">
        Branch <code>{report.monitored.asset_id}</code>
        {rating !== null && (
          <>
            {' '}
            · <Term definition={GLOSSARY.rateA}>rate A</Term> {formatNumber(rating, 'MVA')}
          </>
        )}{' '}
        · <Term definition={GLOSSARY.dcFlow}>DC flow</Term> in the <Term definition={GLOSSARY.tytfs}>TYTFS</Term> 2024 case
      </p>
      <p className="block-hint">
        <span className="change">Purple figures</span> show the change from all equipment in service.
      </p>
      <table className="runs-table">
        <thead>
          <tr>
            <th scope="col">Situation</th>
            <th scope="col" className="num">
              <Term definition={GLOSSARY.flowSize}>Flow</Term>
            </th>
            <th scope="col" className="num">
              <Term definition={GLOSSARY.loading}>Loading</Term>
            </th>
            <th scope="col" className="num">
              <Term definition={GLOSSARY.headroom}>Headroom</Term>
            </th>
          </tr>
        </thead>
        <tbody>
          {views.map((view) => (
            <tr key={view.name} className={view.status === 'ok' ? undefined : 'row-warning'}>
              <th scope="row" data-label="Situation">
                {view.name === 'selected_n_minus_one' ? (
                  <>
                    Planned outage + <Term definition={GLOSSARY.nMinusOne}>selected N-1</Term>
                  </>
                ) : (
                  view.label
                )}
                {view.status !== 'ok' && <span className="cell-note">{SOLVER_TEXT[view.status]}</span>}
              </th>
              <td className="num" data-label="Flow">
                <span className="value">{formatNumber(view.flowSize, 'MW', 1)}</span>
                <Change value={view.sizeChange} unit="MW" />
              </td>
              <td className="num" data-label="Loading">
                <span className="value">{formatPercent(view.loadingPct, 1)}</span>
                {view.severity !== 'normal' && (
                  <Term definition={GLOSSARY.loadingBand}>
                    <span className={`tag tag-${view.severity}`}>{SEVERITY_TEXT[view.severity]}</span>
                  </Term>
                )}
                <Change value={view.loadingChange} unit="pts" />
              </td>
              <td className="num" data-label="Headroom">
                <span className="value">{formatNumber(view.headroom, 'MW')}</span>
                <Change value={view.headroomChange} unit="MW" digits={0} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="block-hint">
        Flow is shown without direction. Signed flow follows the planning-case branch orientation:{' '}
        {views.map((view) => `${view.label} ${formatNumber(view.signedFlow, 'MW', 1)}`).join('; ')}.
      </p>
    </div>
  );
}

export default MonitorRunsTable;

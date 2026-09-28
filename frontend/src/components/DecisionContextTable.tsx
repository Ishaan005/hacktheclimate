import type { DecisionContextInterval } from '../types';
import { COPY } from '../copy';
import { formatDateTime, formatNumber, formatTime } from '../format';

type DecisionContextTableProps = {
  issuedAt: string;
  context: DecisionContextInterval[];
};

// Shows every 3rd hour to stay readable on narrow screens.
function DecisionContextTable({ issuedAt, context }: DecisionContextTableProps) {
  const rows = context.filter((_, index) => index % 6 === 0);
  return (
    <div className="block context">
      <h3>{COPY.contextTitle}</h3>
      <p className="context-issued">Forecast issued {formatDateTime(issuedAt)}</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Target (UTC)</th>
              <th scope="col">100 m wind speed forecast</th>
              <th scope="col">Solar radiation forecast</th>
              <th scope="col">Latest demand at decision time</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.target_timestamp}>
                <th scope="row">{formatTime(row.target_timestamp)}</th>
                <td>{formatNumber(row.wind_speed_100m_ms, 'm/s', 1)}</td>
                <td>{formatNumber(row.solar_radiation_w_m2, 'W/m²')}</td>
                <td>{formatNumber(row.demand_lag_mw, 'MW')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DecisionContextTable;

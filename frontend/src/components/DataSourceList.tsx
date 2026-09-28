import type { DataSource, SourceStatus } from '../types';
import { formatDateTime } from '../format';

// Staleness depends on each source's publication cycle, so only a status
// sent by the API is shown; the UI does not guess from dates.
const STATUS_TEXT: Record<SourceStatus, string> = {
  current: 'Current',
  stale: 'Stale',
  unavailable: 'Unavailable',
};

function DataSourceList({ sources }: { sources: DataSource[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="block sources">
      <h3>Sources</h3>
      <ul>
        {sources.map((item) => (
          <li key={item.source} className={`source${item.status ? ` source-${item.status}` : ''}`}>
            <span className="source-name">
              {item.source}
              {item.status && <span className="source-status"> · {STATUS_TEXT[item.status]}</span>}
            </span>
            <span className="source-meta">
              {item.vintage ?? 'Vintage not stated'}
              {item.retrieved_at && ` · ${formatDateTime(item.retrieved_at)}`}
            </span>
            {item.note && <span className="source-note">{item.note}</span>}
            {item.attribution && <span className="source-note">{item.attribution}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default DataSourceList;

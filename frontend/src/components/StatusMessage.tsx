import { STATE_COPY } from '../copy';
import './StatusMessage.css';

type StatusMessageProps = {
  tone: 'loading' | 'error' | 'unavailable' | 'empty' | 'stale';
  title: string;
  consequence: string;
  detail?: string;
  // Short list under the consequence, e.g. the facts still missing.
  items?: string[];
  onRetry?: () => void;
  retryLabel?: string;
};

// Leads with what the operator can or cannot rely on; the technical reason
// follows in smaller text.
function StatusMessage({ tone, title, consequence, detail, items, onRetry, retryLabel }: StatusMessageProps) {
  return (
    <div className={`status status-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <p className="status-title">{title}</p>
      <p className="status-consequence">{consequence}</p>
      {items && items.length > 0 && (
        <ul className="status-items">
          {items.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}
      {detail && <p className="status-detail">Reason: {detail}</p>}
      {onRetry && (
        <button type="button" className="button-secondary" onClick={onRetry}>
          {retryLabel ?? STATE_COPY.retry}
        </button>
      )}
    </div>
  );
}

export default StatusMessage;

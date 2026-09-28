import { STATE_COPY } from '../copy';
import './StatusMessage.css';

type StatusMessageProps = {
  tone: 'loading' | 'error' | 'unavailable' | 'empty' | 'stale';
  title: string;
  consequence: string;
  detail?: string;
  onRetry?: () => void;
};

// Leads with what the operator can or cannot rely on; the technical reason
// follows in smaller text.
function StatusMessage({ tone, title, consequence, detail, onRetry }: StatusMessageProps) {
  return (
    <div className={`status status-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <p className="status-title">{title}</p>
      <p className="status-consequence">{consequence}</p>
      {detail && <p className="status-detail">Reason: {detail}</p>}
      {onRetry && (
        <button type="button" className="button-secondary" onClick={onRetry}>
          {STATE_COPY.retry}
        </button>
      )}
    </div>
  );
}

export default StatusMessage;

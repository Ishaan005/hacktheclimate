type StatusMessageProps = {
  tone: 'loading' | 'error' | 'unavailable' | 'empty';
  message: string;
  detail?: string;
};

function StatusMessage({ tone, message, detail }: StatusMessageProps) {
  return (
    <div className={`status status-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <p>{message}</p>
      {detail && <p className="status-detail">{detail}</p>}
    </div>
  );
}

export default StatusMessage;

import type { ReactNode } from 'react';

type Props = {
  label: string;
  value: ReactNode;
  detail?: string;
  priority?: 'primary' | 'secondary';
};

function MetricCard({ label, value, detail, priority = 'primary' }: Props) {
  return (
    <div className={`metric metric-${priority}`}>
      <dt className="metric-label">{label}</dt>
      <dd className="metric-value">{value}</dd>
      {detail && <dd className="metric-detail">{detail}</dd>}
    </div>
  );
}

export default MetricCard;

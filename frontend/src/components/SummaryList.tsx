import type { ReactNode } from 'react';

export type SummaryRow = {
  key: string;
  value: ReactNode;
  hint?: ReactNode;
};

// Key/value rows in the style of public-sector summary lists.
function SummaryList({ rows, className = '' }: { rows: SummaryRow[]; className?: string }) {
  return (
    <dl className={`summary-list ${className}`.trim()}>
      {rows.map((row) => (
        <div className="summary-row" key={row.key}>
          <dt>{row.key}</dt>
          <dd>
            {row.value}
            {row.hint && <span className="summary-hint">{row.hint}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default SummaryList;

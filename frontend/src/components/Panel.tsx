import type { ReactNode } from 'react';
import './Panel.css';

type PanelProps = {
  title: string;
  scope: string;
  caveat: string;
  variant: 'forecast' | 'scenario';
  kind: string;
  children: ReactNode;
};

// Title, scope and caveat render in every state so the two products are
// never confused, even while loading or after an error.
function Panel({ title, scope, caveat, variant, kind, children }: PanelProps) {
  const headingId = `${variant}-heading`;
  return (
    <section className={`panel panel-${variant}`} aria-labelledby={headingId}>
      <header className="panel-header">
        <p className="eyebrow">{kind}</p>
        <h2 id={headingId}>{title}</h2>
        <p className="panel-scope">{scope}</p>
      </header>
      <div className="panel-body">{children}</div>
      <p className="panel-caveat">
        <strong>Limits: </strong>
        {caveat}
      </p>
    </section>
  );
}

export default Panel;

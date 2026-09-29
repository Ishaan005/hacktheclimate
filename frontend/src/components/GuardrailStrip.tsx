import { GUARDRAIL_LABEL, GUARDRAIL_STATUS_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import type { Guardrail, GuardrailStatus } from '../types';
import StatusChip from './StatusChip';

// Sentence case for a name this build has no label for: min_generation
// becomes "Min generation".
function fallbackLabel(name: string): string {
  const words = name.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const STATUS_ORDER: GuardrailStatus[] = ['breach', 'unknown', 'within_modelled_limit'];

// One row per safety constraint so baseline and post-action read down in columns.
// Rows whose status changes are highlighted; the rest are context. A row
// with a breach on either side takes a red bar instead of the blue one.
function GuardrailStrip({ guardrails }: { guardrails: Guardrail[] }) {
  const counts = STATUS_ORDER.map((status) => ({
    status,
    count: guardrails.filter((item) => item.postAction === status).length,
  })).filter((item) => item.count > 0);
  return (
    <section className="card card-guardrails" aria-labelledby="guardrail-heading">
      <h3 id="guardrail-heading" className="card-kicker">
        {WORKSPACE_COPY.guardrailTitle}
        <span className="guardrail-summary">
          {WORKSPACE_COPY.postAction}:{' '}
          {counts.map((item) => `${item.count} ${GUARDRAIL_STATUS_LABEL[item.status].toLowerCase()}`).join(', ')}
        </span>
      </h3>
      <table className="guardrail-table">
        <thead>
          <tr>
            <th scope="col">Constraint</th>
            <th scope="col">{WORKSPACE_COPY.baseline}</th>
            <th scope="col">{WORKSPACE_COPY.postAction}</th>
            <th scope="col">Margin</th>
          </tr>
        </thead>
        <tbody>
          {guardrails.map((item) => {
            const changed = item.baseline !== item.postAction;
            const breach = item.baseline === 'breach' || item.postAction === 'breach';
            const className = [changed && 'guardrail-changed', breach && 'guardrail-breach'].filter(Boolean).join(' ');
            return (
              <tr key={item.name} className={className || undefined}>
                <th scope="row">
                  {/* A solver may send a name this build does not know. */}
                  {GUARDRAIL_LABEL[item.name] ?? fallbackLabel(item.name)}
                  {item.note && <span className="guardrail-note">{item.note}</span>}
                </th>
                <td><StatusChip status={item.baseline} prefix={WORKSPACE_COPY.baseline} /></td>
                <td><StatusChip status={item.postAction} prefix={WORKSPACE_COPY.postAction} /></td>
                <td className="mono guardrail-meta">
                  {item.margin ?? 'Unknown'}
                  {item.timestamp && ` · ${formatTime(item.timestamp)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

export default GuardrailStrip;

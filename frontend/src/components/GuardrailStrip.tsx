import { GUARDRAIL_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import type { Guardrail } from '../types';
import StatusChip from './StatusChip';

function GuardrailStrip({ guardrails }: { guardrails: Guardrail[] }) {
  return (
    <section className="card card-guardrails" aria-labelledby="guardrail-heading">
      <h3 id="guardrail-heading" className="card-kicker">{WORKSPACE_COPY.guardrailTitle}</h3>
      <ul className="guardrails">
        {guardrails.map((item) => {
          const label = GUARDRAIL_LABEL[item.name];
          return (
            <li key={item.name} className="guardrail" aria-label={label}>
              <span className="guardrail-name">{label}</span>
              <span className="guardrail-states">
                <StatusChip status={item.baseline} prefix={WORKSPACE_COPY.baseline} />
                <span aria-hidden="true">to</span>
                <StatusChip status={item.postAction} prefix={WORKSPACE_COPY.postAction} />
              </span>
              <span className="guardrail-meta mono">
                Margin {item.margin ?? 'unknown'}
                {item.timestamp && ` · ${formatTime(item.timestamp)}`}
              </span>
              {item.note && <span className="guardrail-note">{item.note}</span>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default GuardrailStrip;

import { WORKSPACE_COPY } from '../copy';
import type { BindingCondition } from '../types';
import StatusChip from './StatusChip';

function BindingConditionCard({ binding }: { binding: BindingCondition | null }) {
  return (
    <section className={`card card-binding card-binding-${binding?.status ?? 'unknown'}`} aria-labelledby="binding-heading">
      <h3 id="binding-heading" className="card-kicker">{WORKSPACE_COPY.bindingTitle}</h3>
      {binding ? (
        <>
          <p className="card-headline">
            {binding.type} <StatusChip status={binding.status} prefix="Binding status" />
          </p>
          <dl className="fields">
            <div><dt>Limiting metric</dt><dd>{binding.metric}</dd></div>
            <div><dt>Location</dt><dd>{binding.location ?? 'Unknown'}</dd></div>
            <div><dt>Margin to limit</dt><dd className="mono">{binding.margin ?? 'Unknown'}</dd></div>
          </dl>
        </>
      ) : (
        <p className="card-headline">{WORKSPACE_COPY.bindingNone}</p>
      )}
    </section>
  );
}

export default BindingConditionCard;

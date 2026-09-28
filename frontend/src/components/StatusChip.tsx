import { GUARDRAIL_STATUS_LABEL } from '../copy';
import type { GuardrailStatus } from '../types';

type Props = {
  status: GuardrailStatus;
  prefix?: string;
};

// Green only for within_modelled_limit, red only for breach, amber for
// unknown. Unknown is never shown as a positive state.
function StatusChip({ status, prefix }: Props) {
  return (
    <span className={`chip chip-${status}`}>
      {prefix && <span className="visually-hidden">{prefix}: </span>}
      {GUARDRAIL_STATUS_LABEL[status]}
    </span>
  );
}

export default StatusChip;

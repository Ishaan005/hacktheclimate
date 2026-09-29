import { PLAN_LABEL, RESULT_LABEL } from '../../decision/copy/shared';
import type { PlanLabel, SafetyResult } from '../../decision/types';

// Green only for pass and actionable, red for fail and unsafe, amber for the
// rest. Unknown never looks positive.
const RESULT_TONE: Record<SafetyResult, string> = {
  pass: 'chip-within_modelled_limit',
  fail: 'chip-breach',
  unknown: 'chip-unknown',
};

const PLAN_TONE: Record<PlanLabel, string> = {
  actionable: 'chip-within_modelled_limit',
  conditional: 'chip-unknown',
  unsafe: 'chip-breach',
  insufficient_evidence: 'chip-unknown',
};

export function ResultChip({ result, prefix }: { result: SafetyResult; prefix?: string }) {
  return (
    <span className={`chip ${RESULT_TONE[result]}`}>
      {prefix && <span className="visually-hidden">{prefix}: </span>}
      {RESULT_LABEL[result]}
    </span>
  );
}

export function PlanLabelChip({ label }: { label: PlanLabel }) {
  return <span className={`chip ${PLAN_TONE[label]}`}>{PLAN_LABEL[label]}</span>;
}

import { DECISION_COPY } from '../../decision/copy/workspace';
import { planLabel } from '../../decision/rules';
import { PLAN_LABEL, RESULT_LABEL } from '../../decision/copy/shared';
import { FAMILY_LABEL, familyOf, suggestionByKey } from '../../decision/scope';
import type { Assessment, OverallSafety, Plan } from '../../decision/types';
import { PlanLabelChip, ResultChip } from './ResultChip';

type Props = {
  assessment: Assessment;
  overall: OverallSafety;
  plan: Plan | null;
  stale: boolean;
  demo?: boolean;
};

// Three operator questions in one band above the detail: what is binding,
// is it safe, and what is proposed. Safety sits before the plan so a plan
// label is always read against it.
function DecisionSummary({ assessment, overall, plan, stale, demo = false }: Props) {
  const label = plan ? planLabel(plan, assessment, stale) : null;
  return (
    <section className="card decision-summary" aria-labelledby="decision-summary-title">
      <h2 id="decision-summary-title" className="visually-hidden">{DECISION_COPY.summaryTitle}</h2>
      <div className="decision-summary-item decision-summary-binding">
        <p className="decision-summary-label">{DECISION_COPY.summaryBinding}</p>
        {assessment.conditions.length ? (
          <ul className="decision-summary-conditions">
            {assessment.conditions.map((condition) => (
              <li key={`${condition.scenarioId}-${condition.situationKey}`}>
                <span className="decision-summary-family">{FAMILY_LABEL[familyOf(condition.scenarioId)]}</span>
                <span>{suggestionByKey(condition.situationKey)?.text ?? FAMILY_LABEL[familyOf(condition.scenarioId)]}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="decision-summary-value">{DECISION_COPY.summaryNoBinding}</p>
        )}
      </div>
      <div className="decision-summary-item">
        <p className="decision-summary-label">{DECISION_COPY.summarySafety}</p>
        <p className="decision-summary-value">{demo ? RESULT_LABEL[overall.result] : <ResultChip result={overall.result} prefix={DECISION_COPY.summarySafety} />}</p>
        {!demo && <p className="decision-summary-reason">{overall.reason}</p>}
      </div>
      <div className="decision-summary-item">
        <p className="decision-summary-label">{DECISION_COPY.summaryPlan}</p>
        {plan && label ? (
          <>
            <p className="decision-summary-value">{demo ? PLAN_LABEL[label.label] : <PlanLabelChip label={label.label} />}</p>
            {!demo && <p className="decision-summary-reason">{plan.name}</p>}
          </>
        ) : (
          <p className="decision-summary-value">{DECISION_COPY.summaryNoPlan}</p>
        )}
      </div>
    </section>
  );
}

export default DecisionSummary;

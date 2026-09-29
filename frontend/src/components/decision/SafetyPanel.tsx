import { useId } from 'react';
import { ACTION_KIND_LABEL } from '../../decision/actionLabels';
import { STALE_NOTE } from '../../decision/copy/shared';
import { SAFETY_COPY } from '../../decision/copy/safety';
import { checksForPlan, combineResults } from '../../decision/rules';
import { FAMILY_LABEL, familyOf } from '../../decision/scope';
import type { Assessment, OverallSafety, Plan, SafetyCheck, ScenarioFamily, ViewMode } from '../../decision/types';
import { formatDateTime } from '../../format';
import { ResultChip } from './ResultChip';
import './SafetyPanel.css';

type SafetyPanelProps = {
  assessment: Assessment;
  // Already passed through displayOverall(); never recomputed here.
  overall: OverallSafety;
  plan: Plan | null;
  view: ViewMode;
  stale: boolean;
};

const COLUMNS = SAFETY_COPY.columns;

// Families named by the binding conditions, in order, then any other family
// the backend sent checks for, so no returned result is hidden.
function familyOrder(assessment: Assessment): ScenarioFamily[] {
  const order: ScenarioFamily[] = [];
  for (const condition of assessment.conditions) {
    const family = familyOf(condition.scenarioId);
    if (!order.includes(family)) order.push(family);
  }
  for (const check of assessment.familyChecks) {
    if (check.family !== 'cross_family' && !order.includes(check.family)) order.push(check.family);
  }
  return order;
}

// Keep unknown gates in the assessment, but only show checks with a result or
// an actual studied value in the operator table.
function hasDisplayData(check: SafetyCheck): boolean {
  return check.result !== 'unknown' || [check.value, check.margin, check.worstFailure].some((value) => value !== null);
}

function show(value: string | null): string {
  return value ?? '—';
}

// Action checks carry goNoGo; other checks do not.
function CheckTable({ checks, caption }: { checks: (SafetyCheck & { goNoGo?: boolean })[]; caption: string }) {
  const columns = {
    value: checks.some((check) => check.value !== null),
    limit: checks.some((check) => check.limit !== null),
    margin: checks.some((check) => check.margin !== null),
    worstTime: checks.some((check) => check.worstTime !== null),
    worstFailure: checks.some((check) => check.worstFailure !== null),
    source: checks.some((check) => check.source !== null),
  };
  return (
    <table className="safety-table">
      <caption className="visually-hidden">{caption}</caption>
      <thead>
        <tr>
          <th scope="col">{COLUMNS.check}</th>
          {columns.value && <th scope="col">{COLUMNS.value}</th>}
          {columns.limit && <th scope="col">{COLUMNS.limit}</th>}
          {columns.margin && <th scope="col">{COLUMNS.margin}</th>}
          {columns.worstTime && <th scope="col">{COLUMNS.worstTime}</th>}
          {columns.worstFailure && <th scope="col">{COLUMNS.worstFailure}</th>}
          {columns.source && <th scope="col">{COLUMNS.source}</th>}
          <th scope="col">{COLUMNS.result}</th>
        </tr>
      </thead>
      <tbody>
        {checks.map((check) => {
          const goNoGo = check.goNoGo === true;
          return (
            <tr key={check.id} className={`safety-row safety-row-${check.result}`} data-check-id={check.id}>
              <th scope="row">
                {goNoGo && <span className="safety-go-no-go">{SAFETY_COPY.goNoGo}</span>}
                {check.label}
              </th>
              {columns.value && <td className="mono" data-label={COLUMNS.value}>{show(check.value)}</td>}
              {columns.limit && <td className="mono" data-label={COLUMNS.limit}>{show(check.limit)}</td>}
              {columns.margin && <td className="mono" data-label={COLUMNS.margin}>{show(check.margin)}</td>}
              {columns.worstTime && <td className="mono" data-label={COLUMNS.worstTime}>{check.worstTime ? formatDateTime(check.worstTime) : '—'}</td>}
              {columns.worstFailure && <td data-label={COLUMNS.worstFailure}>{show(check.worstFailure)}</td>}
              {columns.source && <td data-label={COLUMNS.source}>{show(check.source)}</td>}
              <td data-label={COLUMNS.result} className="safety-result-cell">
                <ResultChip result={check.result} prefix={check.label} />
                <span className="safety-reason">{check.reason}</span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function SafetyPanel({ assessment, overall, plan, view, stale }: SafetyPanelProps) {
  const headingId = useId();
  const familyChecks = assessment.familyChecks.filter(hasDisplayData);
  const families = familyOrder(assessment).filter((family) => familyChecks.some((check) => check.family === family));
  const crossChecks = assessment.crossChecks.filter(hasDisplayData);
  const allIslandChecks = assessment.allIslandChecks.filter(hasDisplayData);
  const planChecks = plan ? checksForPlan(plan, assessment.actionChecks) : [];
  const visiblePlanChecks = planChecks.filter(hasDisplayData);

  return (
    <section className="safety-panel" aria-labelledby={headingId}>
      <h2 id={headingId} className="safety-title">{SAFETY_COPY.title}</h2>

      <div className={`safety-overall safety-overall-${overall.result}`}>
        <div className="safety-overall-head">
          <span className="safety-overall-label">{SAFETY_COPY.overallLabel}</span>
          <span className="safety-overall-chip">
            <ResultChip result={overall.result} prefix={SAFETY_COPY.overallLabel} />
          </span>
        </div>
        <p className="safety-overall-reason">{overall.reason}</p>
        {stale && <p className="safety-note safety-note-warning" role="status">{STALE_NOTE}</p>}
        {!assessment.validated && <p className="safety-note safety-note-warning">{SAFETY_COPY.notValidated}</p>}
      </div>

      {families.length > 0 && <section className="safety-section" aria-label={SAFETY_COPY.familyChecksTitle}>
        <h3 className="safety-section-title">{SAFETY_COPY.familyChecksTitle}</h3>
        {families.map((family) => {
          const checks = familyChecks.filter((check) => check.family === family);
          return (
            <div key={family} className="safety-family">
              <h4 className="safety-family-title">{FAMILY_LABEL[family]}</h4>
              <CheckTable checks={checks} caption={FAMILY_LABEL[family]} />
            </div>
          );
        })}
      </section>}

      {crossChecks.length > 0 && <section className="safety-section" aria-label={SAFETY_COPY.crossChecksTitle}>
        <h3 className="safety-section-title">{SAFETY_COPY.crossChecksTitle}</h3>
        <p className="safety-hint">{SAFETY_COPY.crossChecksNote}</p>
        <CheckTable checks={crossChecks} caption={SAFETY_COPY.crossChecksTitle} />
      </section>}

      {/* Site view keeps the all-island limits in plain sight. */}
      {view === 'site' && allIslandChecks.length > 0 && (
        <section className="safety-section" aria-label={SAFETY_COPY.allIslandTitle}>
          <h3 className="safety-section-title">{SAFETY_COPY.allIslandTitle}</h3>
          <CheckTable checks={allIslandChecks} caption={SAFETY_COPY.allIslandTitle} />
        </section>
      )}

      {plan && visiblePlanChecks.length > 0 && <section className="safety-section" aria-label={SAFETY_COPY.actionChecksTitle}>
        <h3 className="safety-section-title">{SAFETY_COPY.actionChecksTitle}</h3>
        <p className="safety-hint">{SAFETY_COPY.actionChecksNote}</p>
        {plan?.steps.map((step, index) => {
          // Go/no-go first, then the rest in backend order.
          const checks = planChecks
            .filter((check) => check.stepId === step.id)
            .sort((a, b) => Number(b.goNoGo) - Number(a.goNoGo));
          // Display aggregation only: the worst result of this step's checks.
          if (!checks.some(hasDisplayData)) return null;
          const worst = combineResults(checks.map((check) => check.result));
          return (
            <details key={step.id} className="safety-step" data-step-id={step.id}>
              <summary className="safety-step-summary">
                <span className="safety-step-text">
                  <span className="safety-step-kind">
                    {SAFETY_COPY.step} {index + 1}: {ACTION_KIND_LABEL[step.kind]}
                  </span>
                  <span className="safety-step-instruction">{step.instruction}</span>
                </span>
                <ResultChip result={worst} prefix={`${SAFETY_COPY.step} ${index + 1}`} />
              </summary>
              <CheckTable checks={checks.filter(hasDisplayData)} caption={`${SAFETY_COPY.step} ${index + 1}: ${ACTION_KIND_LABEL[step.kind]}`} />
            </details>
          );
        })}
      </section>}
    </section>
  );
}

export default SafetyPanel;

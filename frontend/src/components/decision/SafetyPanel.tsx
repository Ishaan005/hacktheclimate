import { useId, useState } from 'react';
import { ACTION_KIND_LABEL } from '../../decision/actionLabels';
import { SAFETY_COPY } from '../../decision/copy/safety';
import { checksForPlan, combineResults } from '../../decision/rules';
import { FAMILY_LABEL, familyOf } from '../../decision/scope';
import type { Assessment, OverallSafety, Plan, SafetyCheck, SafetyResult, ScenarioFamily, ViewMode } from '../../decision/types';
import { formatDateTime } from '../../format';
import { ResultChip } from './ResultChip';
import './SafetyPanel.css';

type SafetyPanelProps = {
  assessment: Assessment;
  // Already passed through displayOverall(); never recomputed here.
  overall: OverallSafety;
  plan: Plan | null;
  view: ViewMode;
};

// Action checks carry goNoGo; other checks do not.
type Check = SafetyCheck & { goNoGo?: boolean };

type Field = { key: string; label: string; text: string };

type ListItem =
  | { kind: 'row'; check: Check }
  | { kind: 'group'; reason: string; checks: Check[] };

const FIELDS = SAFETY_COPY.fields;
// This many unknown checks with one reason share a single reason line.
const SHARED_REASON_MIN = 3;

// Security first: failures, then unknowns, then passes.
const RESULT_ORDER: Record<SafetyResult, number> = { fail: 0, unknown: 1, pass: 2 };

function byResult(checks: Check[]): Check[] {
  return [...checks].sort((a, b) => RESULT_ORDER[a.result] - RESULT_ORDER[b.result]);
}

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

// Null is missing: the field is left out, never shown as zero.
function present(fields: (Field | null)[]): Field[] {
  return fields.filter((field): field is Field => field !== null);
}

function field(key: string, label: string, text: string | null): Field | null {
  return text === null ? null : { key, label, text };
}

function Fields({ fields, className, mono }: { fields: Field[]; className: string; mono?: boolean }) {
  if (!fields.length) return null;
  return (
    <p className={className}>
      {fields.map((item) => (
        <span key={item.key} className="safety-field" data-field={item.key}>
          <span className="safety-field-label">{item.label}</span>{' '}
          <span className={mono ? 'mono safety-field-value' : 'safety-field-value'}>{item.text}</span>
        </span>
      ))}
    </p>
  );
}

function CheckRow({ check, showReason }: { check: Check; showReason: boolean }) {
  const figures = present([
    field('value', FIELDS.value, check.value),
    field('limit', FIELDS.limit, check.limit),
    field('margin', FIELDS.margin, check.margin),
  ]);
  const meta = present([
    field('worstTime', FIELDS.worstTime, check.worstTime && formatDateTime(check.worstTime)),
    // Worst credible failure applies to transmission only.
    check.family === 'transmission' ? field('worstFailure', FIELDS.worstFailure, check.worstFailure) : null,
    field('source', FIELDS.source, check.source),
  ]);
  return (
    <li className="safety-check" data-check-id={check.id} data-result={check.result}>
      <span className="safety-check-label">
        {check.goNoGo && <span className="safety-go-no-go">{SAFETY_COPY.goNoGo}</span>}
        {check.label}
      </span>
      <span className="safety-check-result">
        <ResultChip result={check.result} prefix={check.label} />
      </span>
      <Fields fields={figures} className="safety-check-figures" mono />
      <Fields fields={meta} className="safety-check-meta" />
      {showReason && check.reason && <p className="safety-check-reason">{check.reason}</p>}
    </li>
  );
}

// Unknown checks that share a reason are grouped so it is read once. Every
// check still gets its own row and chip.
function CheckList({ checks, sort = true }: { checks: Check[]; sort?: boolean }) {
  const ordered = sort ? byResult(checks) : checks;
  const counts = new Map<string, number>();
  for (const check of ordered) {
    if (check.result === 'unknown') counts.set(check.reason, (counts.get(check.reason) ?? 0) + 1);
  }
  const items: ListItem[] = [];
  const groups = new Map<string, Check[]>();
  for (const check of ordered) {
    if (check.result !== 'unknown' || (counts.get(check.reason) ?? 0) < SHARED_REASON_MIN) {
      items.push({ kind: 'row', check });
      continue;
    }
    const group = groups.get(check.reason);
    if (group) {
      group.push(check);
    } else {
      const created = [check];
      groups.set(check.reason, created);
      items.push({ kind: 'group', reason: check.reason, checks: created });
    }
  }
  return (
    <ul className="safety-checks">
      {items.map((item) => (item.kind === 'row'
        ? <CheckRow key={item.check.id} check={item.check} showReason />
        : (
          <li key={`group-${item.checks[0].id}`} className="safety-group">
            <p className="safety-group-reason">
              {SAFETY_COPY.sharedReason(item.checks.length)} {item.reason}
            </p>
            <ul className="safety-checks">
              {item.checks.map((check) => <CheckRow key={check.id} check={check} showReason={false} />)}
            </ul>
          </li>
        )))}
    </ul>
  );
}

// Count per result, worst first, e.g. "1 fail, 3 unknown". Shown in the
// family menu so a family that is not on screen still shows its state.
function resultSummary(checks: Check[]): string {
  const parts = (['fail', 'unknown', 'pass'] as SafetyResult[])
    .map((result) => ({ result, count: checks.filter((check) => check.result === result).length }))
    .filter((item) => item.count > 0)
    .map((item) => `${item.count} ${SAFETY_COPY.resultWord[item.result]}`);
  return parts.length ? parts.join(', ') : SAFETY_COPY.noChecksShort;
}

// One family's checks at a time, chosen from a menu. It opens on the first
// family with a failed check, so the worst result is on screen first.
function FamilyChecks({ assessment, families }: { assessment: Assessment; families: ScenarioFamily[] }) {
  const id = useId();
  const checksFor = (family: ScenarioFamily) => assessment.familyChecks.filter((check) => check.family === family);
  const worstFirst = families.find((family) => checksFor(family).some((check) => check.result === 'fail')) ?? families[0];
  const [chosen, setChosen] = useState<ScenarioFamily | undefined>(worstFirst);
  const family = chosen && families.includes(chosen) ? chosen : worstFirst;

  if (!family) {
    return (
      <section aria-labelledby={`${id}-title`}>
        <h3 id={`${id}-title`} className="panel-section-title">{SAFETY_COPY.familyChecksTitle}</h3>
        <p className="safety-empty">{SAFETY_COPY.noConditions}</p>
      </section>
    );
  }
  const checks = checksFor(family);
  return (
    <section className="safety-family" aria-labelledby={`${id}-title`} data-family={family}>
      <div className="safety-family-header">
        <h3 id={`${id}-title`} className="panel-section-title">{SAFETY_COPY.familyChecksTitle}</h3>
        <label className="visually-hidden" htmlFor={`${id}-menu`}>{SAFETY_COPY.familyMenuLabel}</label>
        <select
          id={`${id}-menu`}
          className="input safety-family-menu"
          value={family}
          onChange={(event) => setChosen(event.target.value as ScenarioFamily)}
        >
          {families.map((item) => (
            <option key={item} value={item}>{`${FAMILY_LABEL[item]} (${resultSummary(checksFor(item))})`}</option>
          ))}
        </select>
      </div>
      {checks.length
        ? <CheckList checks={checks} />
        : <p className="safety-empty">{SAFETY_COPY.noFamilyChecks}</p>}
    </section>
  );
}

function SafetyPanel({ assessment, overall, plan, view }: SafetyPanelProps) {
  const id = useId();
  const families = familyOrder(assessment);
  const planChecks = plan ? checksForPlan(plan, assessment.actionChecks) : [];

  return (
    <section className="card safety-panel" aria-labelledby={`${id}-title`}>
      <div className="panel-header">
        <h2 id={`${id}-title`} className="panel-title">{SAFETY_COPY.title}</h2>
        <span className="safety-overall-chip">
          <ResultChip result={overall.result} prefix={SAFETY_COPY.overallLabel} />
        </span>
      </div>
      <p className="safety-overall-reason">{overall.reason}</p>

      <FamilyChecks assessment={assessment} families={families} />

      {/* Site view keeps the all-island limits in plain sight. */}
      {view === 'site' && (
        <section aria-labelledby={`${id}-island`}>
          <h3 id={`${id}-island`} className="panel-section-title">{SAFETY_COPY.allIslandTitle}</h3>
          {assessment.allIslandChecks.length
            ? <CheckList checks={assessment.allIslandChecks} />
            : <p className="safety-empty">{SAFETY_COPY.noAllIslandChecks}</p>}
        </section>
      )}

      <section aria-labelledby={`${id}-action`}>
        <h3 id={`${id}-action`} className="panel-section-title">{SAFETY_COPY.actionChecksTitle}</h3>
        <p className="safety-hint">{plan ? SAFETY_COPY.actionChecksNote : SAFETY_COPY.noPlan}</p>
        {plan?.steps.map((step, index) => {
          // Go/no-go first, then the rest in backend order.
          const checks = planChecks
            .filter((check) => check.stepId === step.id)
            .sort((a, b) => Number(b.goNoGo) - Number(a.goNoGo));
          // Display aggregation only: the worst result of this step's checks.
          const worst = combineResults(checks.map((check) => check.result));
          const stepName = `${SAFETY_COPY.step} ${index + 1}: ${ACTION_KIND_LABEL[step.kind]}`;
          return (
            <details key={step.id} className="safety-step" data-step-id={step.id}>
              <summary className="safety-step-summary">
                <span className="safety-step-text">
                  <span className="safety-step-kind">{stepName}</span>
                  <span className="safety-step-instruction">{step.instruction}</span>
                </span>
                <span className="safety-check-result">
                  <ResultChip result={worst} prefix={`${SAFETY_COPY.step} ${index + 1}`} />
                </span>
              </summary>
              <div className="safety-step-body">
                {checks.length
                  ? <CheckList checks={checks} sort={false} />
                  : <p className="safety-empty">{SAFETY_COPY.noStepChecks}</p>}
              </div>
            </details>
          );
        })}
      </section>
    </section>
  );
}

export default SafetyPanel;

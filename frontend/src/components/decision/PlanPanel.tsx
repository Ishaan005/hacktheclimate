import { useId, useState } from 'react';
import { ACTION_KIND_LABEL } from '../../decision/actionLabels';
import { PERMISSION_STATE_LABEL, PLAN_COPY, ROLE_LABEL, permissionText } from '../../decision/copy/plan';
import { RESULT_LABEL, STALE_NOTE } from '../../decision/copy/shared';
import { planLabel } from '../../decision/rules';
import { isDemoSource } from '../../decision/source';
import { copyAsAlternative } from '../../decision/useDecisionWorkspace';
import type { ActionKind, Assessment, PermissionState, Plan, PlanStep, SafetyCheck } from '../../decision/types';
import { formatNumber, formatSigned, formatTime, parseUtc } from '../../format';
import { PlanLabelChip } from './ResultChip';
import './PlanPanel.css';

type Props = {
  assessment: Assessment;
  alternative: Plan | null;
  stale: boolean;
  onEditStep: (stepId: string, changes: Partial<PlanStep>) => void;
  onSetAlternative: (plan: Plan | null) => void;
  onRerun: () => void;
};

const ROLE_ORDER: Record<PlanStep['role'], number> = { main: 0, supporting: 1, parallel: 2 };
const PERMISSION_STATES: PermissionState[] = ['pending', 'confirmed', 'refused', 'unknown'];

// Main action first, then supporting and parallel steps. The sort is stable,
// so steps keep the backend order within a role.
function sortSteps(steps: PlanStep[]): PlanStep[] {
  return [...steps].sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role]);
}

function allChecks(assessment: Assessment): Map<string, SafetyCheck> {
  const checks = [...assessment.familyChecks, ...assessment.crossChecks, ...assessment.allIslandChecks, ...assessment.actionChecks];
  return new Map(checks.map((check) => [check.id, check]));
}

// What still blocks a step: listed checks by label, plus any clearance or
// acceptance that is not yet confirmed.
function blockers(step: PlanStep, checks: Map<string, SafetyCheck>): string[] {
  const unknown: string[] = [];
  const items = step.blockingCheckIds.flatMap((id) => {
    const check = checks.get(id);
    if (!check || check.result === 'unknown') {
      unknown.push(id);
      return [];
    }
    return [`${check.label} (${RESULT_LABEL[check.result]})`];
  });
  if (unknown.length) items.push(`${unknown.length} safety ${unknown.length === 1 ? 'check needs' : 'checks need'} evidence`);
  if (step.permissionRoute !== 'direct' && step.permissionState !== 'confirmed') {
    items.push(PLAN_COPY.permissionPending(step.permissionParty ?? step.executor, step.permissionState));
  }
  return items;
}

function dependencies(step: PlanStep, plan: Plan): string[] {
  return step.dependsOn.map((id) => plan.steps.find((other) => other.id === id)?.instruction ?? `${PLAN_COPY.removedStep} (${id})`);
}

function stepHeading(step: PlanStep, index: number): string {
  return `${PLAN_COPY.stepTitle} ${index + 1} · ${ROLE_LABEL[step.role]} · ${ACTION_KIND_LABEL[step.kind]}`;
}

// Timing, blockers and dependencies, shared by both read-only and edited steps.
function StepFacts({ step, plan, checks, readOnlyCore }: { step: PlanStep; plan: Plan; checks: Map<string, SafetyCheck>; readOnlyCore: boolean }) {
  const blocking = blockers(step, checks);
  const after = dependencies(step, plan);
  return (
    <>
      <dl className="fields plan-step-fields">
        {readOnlyCore && (
          <>
            <div className="plan-field-wide">
              <dt>{PLAN_COPY.fields.instruction}</dt>
              <dd className="plan-instruction">{step.instruction}</dd>
            </div>
            <div>
              <dt>{PLAN_COPY.fields.executor}</dt>
              <dd>{step.executor}</dd>
            </div>
          </>
        )}
        <div>
          <dt>{PLAN_COPY.fields.permission}</dt>
          <dd>
            {permissionText(step.permissionRoute, step.permissionParty)}
            {step.permissionRoute !== 'direct' && (
              <span className={`plan-permission-state plan-permission-${step.permissionState}`}> · {PERMISSION_STATE_LABEL[step.permissionState]}</span>
            )}
          </dd>
        </div>
        {readOnlyCore && step.startTime && (
          <div>
            <dt>{PLAN_COPY.fields.startTime}</dt>
            <dd className="mono">{formatTime(step.startTime)}</dd>
          </div>
        )}
        {step.effectTime && <div>
          <dt>{PLAN_COPY.fields.effectTime}</dt>
          <dd className="mono">{formatTime(step.effectTime)}</dd>
        </div>}
        {readOnlyCore && (
          <>
            {step.durationMinutes !== null && <div>
              <dt>{PLAN_COPY.fields.duration}</dt>
              <dd className="mono">{formatNumber(step.durationMinutes, 'min')}</dd>
            </div>}
            {step.mwEffect !== null && <div>
              <dt>{PLAN_COPY.fields.mwEffect}</dt>
              <dd className="mono" title={PLAN_COPY.mwHint}>{formatSigned(step.mwEffect, 'MW')}</dd>
            </div>}
          </>
        )}
      </dl>
      <div className="plan-step-links">
        {blocking.length > 0 && <p className="plan-blocking">
          <strong>{PLAN_COPY.fields.blocking}: </strong>
          {blocking.join('; ')}
        </p>}
        {after.map((text, i) => (
          <p key={i} className="plan-dependency">{PLAN_COPY.fields.dependsOn}: {text}</p>
        ))}
      </div>
    </>
  );
}

function StepCard({ step, index, plan, checks }: { step: PlanStep; index: number; plan: Plan; checks: Map<string, SafetyCheck> }) {
  const headingId = `${plan.id}-${step.id}-heading`;
  return (
    <li className={`plan-step plan-step-${step.role}`} aria-labelledby={headingId}>
      <h4 id={headingId} className="plan-step-head">{stepHeading(step, index)}</h4>
      <StepFacts step={step} plan={plan} checks={checks} readOnlyCore />
    </li>
  );
}

// ISO UTC to and from a datetime-local value, both in UTC.
function toInputTime(iso: string | null): string {
  if (!iso) return '';
  const date = parseUtc(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 16);
}

function fromInputTime(value: string): string | null {
  if (!value) return null;
  const date = new Date(`${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function parseNumber(text: string): number | null | undefined {
  const trimmed = text.trim().replace('−', '-');
  if (!trimmed) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : undefined;
}

// Keeps the typed text (e.g. '-' or '1.') while only sending valid numbers.
// Empty means not supplied, never zero.
function NumberField({ label, value, hint, onCommit }: { label: string; value: number | null; hint?: string; onCommit: (value: number | null) => void }) {
  const [draft, setDraft] = useState(value === null ? '' : String(value));
  const [seen, setSeen] = useState(value);
  if (value !== seen) {
    setSeen(value);
    setDraft(value === null ? '' : String(value));
  }
  const invalid = parseNumber(draft) === undefined;
  const id = useId();
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>{label}</label>
      <input
        id={id}
        className="input mono"
        inputMode="decimal"
        value={draft}
        aria-invalid={invalid || undefined}
        aria-describedby={hint ? `${id}-hint` : undefined}
        onChange={(event) => {
          const text = event.target.value;
          setDraft(text);
          const parsed = parseNumber(text);
          if (parsed !== undefined) {
            setSeen(parsed);
            onCommit(parsed);
          }
        }}
      />
      {hint && <span id={`${id}-hint`} className="field-hint">{hint}</span>}
    </div>
  );
}

type EditProps = {
  step: PlanStep;
  index: number;
  plan: Plan;
  checks: Map<string, SafetyCheck>;
  onEditStep: Props['onEditStep'];
  onRemove: (stepId: string) => void;
};

function EditableStep({ step, index, plan, checks, onEditStep, onRemove }: EditProps) {
  const headingId = `${plan.id}-${step.id}-heading`;
  const edit = (changes: Partial<PlanStep>) => onEditStep(step.id, changes);
  return (
    <li className={`plan-step plan-step-${step.role} plan-step-editable`} aria-labelledby={headingId}>
      <div className="plan-step-bar">
        <h4 id={headingId} className="plan-step-head">{stepHeading(step, index)}</h4>
        <button type="button" className="button-secondary" onClick={() => onRemove(step.id)}>{PLAN_COPY.removeStep}</button>
      </div>
      <div className="plan-edit-grid">
        <label className="field plan-field-wide">
          <span className="field-label">{PLAN_COPY.edit.instruction}</span>
          <textarea className="input" rows={2} value={step.instruction} onChange={(event) => edit({ instruction: event.target.value })} />
        </label>
        <label className="field">
          <span className="field-label">{PLAN_COPY.edit.executor}</span>
          <input className="input" value={step.executor} onChange={(event) => edit({ executor: event.target.value })} />
        </label>
        <label className="field">
          <span className="field-label">{PLAN_COPY.edit.startTime}</span>
          <input
            className="input mono"
            type="datetime-local"
            value={toInputTime(step.startTime)}
            onChange={(event) => edit({ startTime: fromInputTime(event.target.value) })}
          />
        </label>
        <NumberField label={PLAN_COPY.edit.mwEffect} value={step.mwEffect} hint={PLAN_COPY.mwHint} onCommit={(mwEffect) => edit({ mwEffect })} />
        <NumberField label={PLAN_COPY.edit.duration} value={step.durationMinutes} onCommit={(durationMinutes) => edit({ durationMinutes })} />
        {step.permissionRoute !== 'direct' && (
          <label className="field">
            <span className="field-label">{PLAN_COPY.edit.permissionState}</span>
            <select
              className="input"
              value={step.permissionState}
              onChange={(event) => edit({ permissionState: event.target.value as PermissionState })}
            >
              {PERMISSION_STATES.map((state) => (
                <option key={state} value={state}>{PERMISSION_STATE_LABEL[state]}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      <StepFacts step={step} plan={plan} checks={checks} readOnlyCore={false} />
    </li>
  );
}

function LabelLine({ plan, assessment, stale }: { plan: Plan; assessment: Assessment; stale: boolean }) {
  const { label, reason } = planLabel(plan, assessment, stale);
  const repeatedDemoWarning = isDemoSource(assessment.context.sourceKind) && label === 'insufficient_evidence' && !stale;
  return (
    <p className="plan-label">
      <span className="visually-hidden">{PLAN_COPY.labelTitle}: </span>
      <PlanLabelChip label={label} />
      {!repeatedDemoWarning && <span className="plan-label-reason">{reason}</span>}
    </p>
  );
}

// Right panel: the proposed plan, read-only, and an optional operator
// alternative beside it. Nothing here sends an instruction.
function PlanPanel({ assessment, alternative, stale, onEditStep, onSetAlternative, onRerun }: Props) {
  const proposed = assessment.proposed;
  const checks = allChecks(assessment);
  const [newKind, setNewKind] = useState<ActionKind>('local_storage_or_demand');

  function addStep() {
    const step: PlanStep = {
      id: `operator-step-${Date.now()}-${alternative?.steps.length ?? 0}`, kind: newKind,
      role: alternative?.steps.length ? 'supporting' : 'main',
      instruction: ACTION_KIND_LABEL[newKind], executor: '',
      permissionRoute: 'needs_acceptance', permissionState: 'unknown',
      permissionParty: null, startTime: null, effectTime: null,
      durationMinutes: null, mwEffect: null, dependsOn: [], blockingCheckIds: [],
    };
    onSetAlternative(alternative
      ? { ...alternative, steps: [...alternative.steps, step] }
      : { id: 'plan-operator', name: 'Operator alternative', origin: 'operator',
        label: 'insufficient_evidence', labelReason: 'Not assessed yet.', steps: [step] });
  }

  function removeStep(stepId: string) {
    if (!alternative) return;
    onSetAlternative({ ...alternative, steps: alternative.steps.filter((step) => step.id !== stepId) });
  }

  return (
    <section className="plan-panel" aria-labelledby="plan-panel-heading">
      <header className="plan-panel-header">
        <h2 id="plan-panel-heading">{PLAN_COPY.title}</h2>
        <p className="plan-no-send">{PLAN_COPY.noSendNote}</p>
      </header>

      {stale && (
        <div className="plan-stale" role="status">
          <p>{STALE_NOTE}</p>
          <button type="button" className="button-primary" onClick={onRerun}>{PLAN_COPY.rerun}</button>
        </div>
      )}

      <section className="plan-section" aria-labelledby="plan-proposed-heading">
        <h3 id="plan-proposed-heading" className="card-kicker">{PLAN_COPY.proposedHeading}</h3>
        {proposed ? (
          <>
            <p className="plan-name">{proposed.name}</p>
            <LabelLine plan={proposed} assessment={assessment} stale={stale} />
            {proposed.steps.length ? (
              <ol className="plan-steps">
                {sortSteps(proposed.steps).map((step, index) => (
                  <StepCard key={step.id} step={step} index={index} plan={proposed} checks={checks} />
                ))}
              </ol>
            ) : (
              <p>{PLAN_COPY.noSteps}</p>
            )}
            {!alternative && (
              <div className="plan-actions">
                <button type="button" className="button-secondary" onClick={() => onSetAlternative(copyAsAlternative(proposed))}>
                  {PLAN_COPY.editAsAlternative}
                </button>
                <p className="field-hint">{PLAN_COPY.editNote}</p>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="card-headline">{PLAN_COPY.noPlan}</p>
            <p>{assessment.overall.reason}</p>
            {!alternative && (
              <div className="plan-actions">
                <label className="field-label" htmlFor="alternative-action-kind">Action to assess</label>
                <select id="alternative-action-kind" className="input" value={newKind}
                  onChange={(event) => setNewKind(event.target.value as ActionKind)}>
                  {(Object.keys(ACTION_KIND_LABEL) as ActionKind[]).map((kind) => (
                    <option key={kind} value={kind}>{ACTION_KIND_LABEL[kind]}</option>
                  ))}
                </select>
                <button type="button" className="button-secondary" onClick={addStep}>Create alternative</button>
              </div>
            )}
          </>
        )}
      </section>

      {alternative && (
        <section className="plan-section plan-section-alternative" aria-labelledby="plan-alternative-heading">
          <div className="plan-step-bar">
            <h3 id="plan-alternative-heading" className="card-kicker">{PLAN_COPY.alternativeHeading}</h3>
            <button type="button" className="button-secondary" onClick={() => onSetAlternative(null)}>{PLAN_COPY.discardAlternative}</button>
          </div>
          <LabelLine plan={alternative} assessment={assessment} stale={stale} />
          <p className="field-hint">{PLAN_COPY.alternativeNote}</p>
          {alternative.steps.length ? (
            <ol className="plan-steps">
              {sortSteps(alternative.steps).map((step, index) => (
                <EditableStep
                  key={step.id}
                  step={step}
                  index={index}
                  plan={alternative}
                  checks={checks}
                  onEditStep={onEditStep}
                  onRemove={removeStep}
                />
              ))}
            </ol>
          ) : (
            <p>{PLAN_COPY.noSteps}</p>
          )}
          <div className="plan-actions">
            <label className="field-label" htmlFor="alternative-add-kind">Add a step</label>
            <select id="alternative-add-kind" className="input" value={newKind}
              onChange={(event) => setNewKind(event.target.value as ActionKind)}>
              {(Object.keys(ACTION_KIND_LABEL) as ActionKind[]).map((kind) => (
                <option key={kind} value={kind}>{ACTION_KIND_LABEL[kind]}</option>
              ))}
            </select>
            <button type="button" className="button-secondary" onClick={addStep}>Add step</button>
          </div>
        </section>
      )}
    </section>
  );
}

export default PlanPanel;

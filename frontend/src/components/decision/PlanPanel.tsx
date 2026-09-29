import { useId, useState } from 'react';
import { ACTION_KIND_LABEL } from '../../decision/actionLabels';
import { PERMISSION_STATE_LABEL, PLAN_COPY } from '../../decision/copy/plan';
import { planLabel } from '../../decision/rules';
import { copyAsAlternative } from '../../decision/useDecisionWorkspace';
import type { ActionKind, Assessment, PermissionState, Plan, PlanStep } from '../../decision/types';
import { formatNumber, formatTime, parseUtc } from '../../format';
import { PlanLabelChip } from './ResultChip';
import './PlanPanel.css';

type Props = {
  assessment: Assessment;
  alternative: Plan | null;
  stale: boolean;
  demo?: boolean;
  onEditStep: (stepId: string, changes: Partial<PlanStep>) => void;
  onSetAlternative: (plan: Plan | null) => void;
};

const ROLE_ORDER: Record<PlanStep['role'], number> = { main: 0, supporting: 1, parallel: 2 };
const PERMISSION_STATES: PermissionState[] = ['pending', 'confirmed', 'refused', 'unknown'];

// Main action first, then supporting and parallel steps. The sort is stable,
// so steps keep the backend order within a role.
function sortSteps(steps: PlanStep[]): PlanStep[] {
  return [...steps].sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role]);
}

function time(iso: string | null): string {
  return iso ? formatTime(iso) : PLAN_COPY.notAvailable;
}

function dependencies(step: PlanStep, plan: Plan): string[] {
  return step.dependsOn.map((id) => plan.steps.find((other) => other.id === id)?.instruction ?? `${PLAN_COPY.removedStep} (${id})`);
}

function stepHeading(step: PlanStep): string {
  if (step.kind === 'paired_redispatch') return 'Redispatch';
  if (step.kind === 'local_storage_or_demand' && /batter|charg/i.test(step.instruction)) return 'Battery charging';
  return ACTION_KIND_LABEL[step.kind];
}

// Permission decides how a step looks. Anything not yet accepted or cleared
// is amber and a refusal is red, so a conditional step never looks as ready
// as a direct or confirmed one.
type PermissionTone = 'ready' | 'conditional' | 'refused';

function permissionTone(step: PlanStep): PermissionTone {
  if (step.permissionRoute === 'direct' || step.permissionState === 'confirmed') return 'ready';
  return step.permissionState === 'refused' ? 'refused' : 'conditional';
}

// The visible plan reads as an instruction and a short timing sequence.
// Clearance and detailed blockers remain part of the assessment logic.
function StepFacts({ step, plan, readOnlyCore, demo = false }: { step: PlanStep; plan: Plan; readOnlyCore: boolean; demo?: boolean }) {
  const after = dependencies(step, plan);
  return (
    <>
      <dl className="fields plan-step-fields">
        {readOnlyCore && (!demo || step.executor) && (
          <div>
            <dt>Where / who</dt>
            <dd>{step.executor || PLAN_COPY.notAvailable}</dd>
          </div>
        )}
        {readOnlyCore && (!demo || step.startTime) && (
          <div>
            <dt>{PLAN_COPY.fields.startTime}</dt>
            <dd>{time(step.startTime)}</dd>
          </div>
        )}
        {(!demo || step.effectTime) && <div>
          <dt>{PLAN_COPY.fields.effectTime}</dt>
          <dd>{time(step.effectTime)}</dd>
        </div>}
        {readOnlyCore && (
          <>
            {(!demo || step.durationMinutes !== null) && <div>
              <dt>{PLAN_COPY.fields.duration}</dt>
              <dd>{formatNumber(step.durationMinutes, 'min')}</dd>
            </div>}
          </>
        )}
      </dl>
      {!demo && after.length > 0 && <p className="plan-dependency">{PLAN_COPY.fields.dependsOn}: {after.join('; ')}</p>}
    </>
  );
}

// Read-only step: the instruction first, as the operator would say it.
function StepCard({ step, plan, demo = false }: { step: PlanStep; plan: Plan; demo?: boolean }) {
  const headingId = `${plan.id}-${step.id}-heading`;
  return (
    <li className={`plan-step plan-step-${permissionTone(step)}`} aria-labelledby={headingId}>
      <div>
        <h4 id={headingId} className="plan-step-instruction">{step.instruction || PLAN_COPY.notAvailable}</h4>
        <p className="plan-step-meta">{stepHeading(step)}</p>
      </div>
      <StepFacts step={step} plan={plan} readOnlyCore demo={demo} />
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
  plan: Plan;
  onEditStep: Props['onEditStep'];
  onRemove: (stepId: string) => void;
};

function EditableStep({ step, plan, onEditStep, onRemove }: EditProps) {
  const headingId = `${plan.id}-${step.id}-heading`;
  const edit = (changes: Partial<PlanStep>) => onEditStep(step.id, changes);
  return (
    <li className={`plan-step plan-step-${permissionTone(step)} plan-step-editable`} aria-labelledby={headingId}>
      <div className="plan-step-bar">
        <h4 id={headingId} className="plan-step-meta">{stepHeading(step)}</h4>
        <button type="button" className="button-ghost plan-button-remove" onClick={() => onRemove(step.id)}>{PLAN_COPY.removeStep}</button>
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
      <StepFacts step={step} plan={plan} readOnlyCore={false} />
    </li>
  );
}

function LabelLine({ plan, assessment, stale }: { plan: Plan; assessment: Assessment; stale: boolean }) {
  const { label, reason } = planLabel(plan, assessment, stale);
  return (
    <p className="plan-label">
      <span className="visually-hidden">{PLAN_COPY.labelTitle}: </span>
      <PlanLabelChip label={label} />
      <span className="plan-label-reason">{reason}</span>
    </p>
  );
}

function ActionKindSelect({ id, value, hintId, onChange }: { id: string; value: ActionKind; hintId?: string; onChange: (kind: ActionKind) => void }) {
  return (
    <select id={id} className="input" value={value} aria-describedby={hintId}
      onChange={(event) => onChange(event.target.value as ActionKind)}>
      {(Object.keys(ACTION_KIND_LABEL) as ActionKind[]).map((kind) => (
        <option key={kind} value={kind}>{ACTION_KIND_LABEL[kind]}</option>
      ))}
    </select>
  );
}

// Right panel: the proposed plan, read-only, and an optional operator
// alternative beside it. Nothing here sends an instruction.
function PlanPanel({ assessment, alternative, stale, onEditStep, onSetAlternative, demo = false }: Props) {
  const proposed = assessment.proposed;
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

  // The proposal's label sits beside the panel title; the alternative
  // carries its own label in its section.
  const proposedLabel = proposed ? planLabel(proposed, assessment, stale) : null;
  const reliefMw = assessment.outcomes.find((outcome) => outcome.column === 'proposed')?.deliveredReliefMw.value ?? null;

  return (
    <section className="card plan-panel" aria-labelledby="plan-panel-heading">
      <header className="panel-header plan-panel-header">
        <div>
          <h2 id="plan-panel-heading" className="panel-title">{PLAN_COPY.title}</h2>
        </div>
        {proposedLabel && !demo && (
          <span>
            <span className="visually-hidden">{PLAN_COPY.labelTitle}: </span>
            <PlanLabelChip label={proposedLabel.label} />
          </span>
        )}
      </header>

      <section className="plan-section" aria-labelledby="plan-proposed-heading">
        {/* Named for screen readers always; shown only beside an alternative. */}
        <h3 id="plan-proposed-heading" className={alternative ? 'panel-section-title' : 'visually-hidden'}>
          {PLAN_COPY.proposedHeading}
        </h3>
        {proposed && proposedLabel ? (
          <>
            <div>
              <p className="plan-name">{proposed.name}</p>
              {reliefMw !== null && (
                <div className="plan-outcome">
                  <span className="plan-outcome-relief">Expected route relief</span>
                  <strong className={reliefMw > 0 ? 'plan-outcome-saved' : undefined}>{formatNumber(reliefMw, 'MW')} {reliefMw > 0 ? 'saved' : 'relief'}</strong>
                </div>
              )}
            </div>
            {proposed.steps.length ? (
              <ol className="plan-steps">
                {sortSteps(proposed.steps).map((step) => (
                  <StepCard key={step.id} step={step} plan={proposed} demo={demo} />
                ))}
              </ol>
            ) : (
              <p className="plan-empty">{PLAN_COPY.noSteps}</p>
            )}
            {!alternative && (
              <div className="plan-actions">
                <button type="button" className="button-secondary" onClick={() => onSetAlternative(copyAsAlternative(proposed))}>
                  {PLAN_COPY.editAsAlternative}
                </button>
                {!demo && <p className="field-hint">{PLAN_COPY.editNote}</p>}
              </div>
            )}
          </>
        ) : (
          <>
            <p className="plan-empty">{PLAN_COPY.noPlan}. {PLAN_COPY.noPlanReason[assessment.overall.result]}</p>
            {!alternative && (
              <div className="field plan-build">
                <label className="field-label" htmlFor="alternative-action-kind">{PLAN_COPY.buildAlternative}</label>
                <span id="alternative-action-kind-hint" className="field-hint">{PLAN_COPY.buildAlternativeHint}</span>
                <div className="plan-build-row">
                  <ActionKindSelect id="alternative-action-kind" hintId="alternative-action-kind-hint" value={newKind} onChange={setNewKind} />
                  <button type="button" className="button-secondary" onClick={addStep}>{PLAN_COPY.createAlternative}</button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {alternative && (
        <section className="plan-section plan-section-alternative" aria-labelledby="plan-alternative-heading">
          <div className="plan-step-bar">
            <h3 id="plan-alternative-heading" className="panel-section-title">{PLAN_COPY.alternativeHeading}</h3>
            <button type="button" className="button-ghost plan-button-remove" onClick={() => onSetAlternative(null)}>
              {PLAN_COPY.discardAlternative}
            </button>
          </div>
          <LabelLine plan={alternative} assessment={assessment} stale={stale} />
          <p className="field-hint">{PLAN_COPY.alternativeNote}</p>
          {alternative.steps.length ? (
            <ol className="plan-steps">
              {sortSteps(alternative.steps).map((step) => (
                <EditableStep
                  key={step.id}
                  step={step}
                  plan={alternative}
                  onEditStep={onEditStep}
                  onRemove={removeStep}
                />
              ))}
            </ol>
          ) : (
            <p className="plan-empty">{PLAN_COPY.noSteps}</p>
          )}
          <div className="field plan-build">
            <label className="field-label" htmlFor="alternative-add-kind">{PLAN_COPY.addStepLabel}</label>
            <div className="plan-build-row">
              <ActionKindSelect id="alternative-add-kind" value={newKind} onChange={setNewKind} />
              <button type="button" className="button-secondary" onClick={addStep}>{PLAN_COPY.addStep}</button>
            </div>
          </div>
        </section>
      )}
    </section>
  );
}

export default PlanPanel;

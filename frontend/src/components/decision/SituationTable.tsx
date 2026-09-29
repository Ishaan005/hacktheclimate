import { useState } from 'react';
import type { FormEvent } from 'react';
import { DATA_STATUS_LABEL, ORIGIN_LABEL } from '../../decision/copy/shared';
import { FACT_GROUP_LABEL, SITUATION_COPY, STATE_COUNT_LABEL } from '../../decision/copy/situation';
import { familyOf } from '../../decision/scope';
import { formatDateTime } from '../../format';
import type {
  ActiveInstruction,
  BindingCondition,
  DataStatus,
  OperatorEdit,
  ScenarioFamily,
  SituationFact,
} from '../../decision/types';
import '../CaseReview.css';
import './SituationTable.css';

type Props = {
  facts: SituationFact[];
  conditions: BindingCondition[];
  activeInstructions: ActiveInstruction[];
  edits: OperatorEdit[];
  onEdit: (id: string, value: number | string | null) => void;
};

type FactGroup = ScenarioFamily | 'general';

const GROUP_ORDER: FactGroup[] = ['general', 'transmission', 'high_frequency_minimum_generation', 'snsp'];

// Only current may look neutral; anything uncertain is amber.
const STATE_TONE: Record<DataStatus, string> = {
  current: 'chip-neutral',
  stale: 'chip-unknown',
  missing: 'chip-unknown',
  conflicting: 'chip-unknown',
};

// Null means not supplied: show Missing, never zero.
function valueText(value: number | string | null, unit: string | null): string {
  if (value === null) return SITUATION_COPY.missing;
  if (!unit) return String(value);
  return unit === '%' ? `${value}%` : `${value} ${unit}`;
}

function provenanceText(fact: SituationFact): string {
  const parts = [fact.source, fact.timestamp ? formatDateTime(fact.timestamp) : null].filter(Boolean);
  return parts.length ? parts.join(' · ') : SITUATION_COPY.noSource;
}

function isEdited(fact: SituationFact, edits: OperatorEdit[]): boolean {
  return fact.editedFrom !== null || edits.some((edit) => edit.factId === fact.id);
}

// Missing rows sit behind a disclosure; stale, conflicting and edited rows
// always stay in view.
function isHidden(fact: SituationFact, edits: OperatorEdit[]): boolean {
  return fact.state === 'missing' && !isEdited(fact, edits);
}

// "8 current · 1 stale · 2 missing": only states that occur.
function stateSummary(facts: SituationFact[]): string {
  return (Object.keys(STATE_COUNT_LABEL) as DataStatus[])
    .map((state) => ({ state, count: facts.filter((fact) => fact.state === state).length }))
    .filter(({ count }) => count > 0)
    .map(({ state, count }) => `${count} ${STATE_COUNT_LABEL[state]}`)
    .join(' · ');
}

// Never ask the operator for a reliable, current feed value.
function canEdit(fact: SituationFact): boolean {
  return fact.editable || fact.state !== 'current';
}

type EditorProps = {
  fact: SituationFact;
  onSave: (value: number | string) => void;
  onCancel: () => void;
};

// Numbers stay numbers: a numeric row cannot be saved as text.
function FactEditor({ fact, onSave, onCancel }: EditorProps) {
  const numeric = typeof fact.value === 'number' || ['MW', 'MWh', 'Hz', '%', 'units', 'min', 'seconds', 'hours', 'MW/min'].includes(fact.unit ?? '');
  const [draft, setDraft] = useState(fact.value === null ? '' : String(fact.value));
  const inputId = `situation-edit-${fact.id}`;
  const invalid = numeric && draft.trim() !== '' && !Number.isFinite(Number(draft));

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim() || invalid) return;
    onSave(numeric ? Number(draft) : draft.trim());
  }

  return (
    <form className="fact-editor" onSubmit={submit}>
      <label htmlFor={inputId} className="visually-hidden">{fact.label}</label>
      <input
        id={inputId}
        className="input"
        type={numeric ? 'number' : 'text'}
        step="any"
        value={draft}
        aria-invalid={invalid || undefined}
        onChange={(event) => setDraft(event.target.value)}
      />
      {fact.unit && <span className="fact-unit">{fact.unit}</span>}
      <button type="submit" className="button-secondary" disabled={!draft.trim() || invalid}>{SITUATION_COPY.save}</button>
      <button type="button" className="button-ghost" onClick={onCancel}>{SITUATION_COPY.cancel}</button>
    </form>
  );
}

type TableProps = {
  group: FactGroup;
  facts: SituationFact[];
  edits: OperatorEdit[];
  onEdit: Props['onEdit'];
  // Distinguishes the missing-facts tables from the default ones.
  idPrefix: string;
};

function FactGroupTable({ group, facts, edits, onEdit, idPrefix }: TableProps) {
  const [editing, setEditing] = useState<string | null>(null);
  const headingId = `${idPrefix}-${group}`;
  return (
    <div className="situation-group">
      <h3 id={headingId} className="panel-section-title">{FACT_GROUP_LABEL[group]}</h3>
      <table className="fact-table situation-facts" aria-labelledby={headingId}>
        <colgroup>
          <col className="situation-col-fact" />
          <col className="situation-col-value" />
          <col className="situation-col-origin" />
          <col className="situation-col-state" />
          <col className="situation-col-action" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">{SITUATION_COPY.fact}</th>
            <th scope="col">{SITUATION_COPY.value}</th>
            <th scope="col">{SITUATION_COPY.origin}</th>
            <th scope="col">{SITUATION_COPY.state}</th>
            <th scope="col"><span className="visually-hidden">{SITUATION_COPY.edit}</span></th>
          </tr>
        </thead>
        <tbody>
          {facts.map((fact) => {
            const missing = fact.value === null;
            const action = missing ? SITUATION_COPY.add : SITUATION_COPY.edit;
            // The first logged edit keeps the original value, even when it
            // was missing; editedFrom covers edits made before this session.
            const firstEdit = edits.find((edit) => edit.factId === fact.id);
            const edited = isEdited(fact, edits);
            const previous = firstEdit ? firstEdit.from : fact.editedFrom;
            // Nothing supplied a missing value, so it has no origin to show.
            const origin = missing || fact.origin === null ? null : ORIGIN_LABEL[fact.origin];
            return (
              <tr key={fact.id}>
                <th scope="row">{fact.label}</th>
                <td data-label={SITUATION_COPY.value}>
                  {editing === fact.id ? (
                    <FactEditor
                      fact={fact}
                      onSave={(value) => {
                        onEdit(fact.id, value);
                        setEditing(null);
                      }}
                      onCancel={() => setEditing(null)}
                    />
                  ) : (
                    <div>
                      <span className={missing ? 'situation-value situation-value-missing' : 'situation-value'}>
                        {valueText(fact.value, fact.unit)}
                      </span>
                      {edited && (
                        <span className="cell-note situation-edited">
                          {SITUATION_COPY.editedWas(valueText(previous, fact.unit))}
                        </span>
                      )}
                      {!missing && <span className="cell-note">{provenanceText(fact)}</span>}
                      {fact.state === 'conflicting' && fact.conflictNote && (
                        <span className="cell-note situation-conflict">{fact.conflictNote}</span>
                      )}
                    </div>
                  )}
                </td>
                <td data-label={SITUATION_COPY.origin} className="situation-origin">{origin}</td>
                <td data-label={SITUATION_COPY.state}>
                  <span className={`chip ${STATE_TONE[fact.state]}`}>{DATA_STATUS_LABEL[fact.state]}</span>
                </td>
                <td className="situation-action">
                  {canEdit(fact) && editing !== fact.id && (
                    <button
                      type="button"
                      className="button-ghost situation-edit"
                      aria-label={`${action} ${fact.label}`}
                      onClick={() => setEditing(fact.id)}
                    >
                      {action}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function InstructionList({ instructions }: { instructions: ActiveInstruction[] }) {
  // Nothing in force: one quiet line, no heading.
  if (instructions.length === 0) {
    return <p className="situation-empty">{SITUATION_COPY.noInstructions}</p>;
  }
  return (
    <div className="situation-group">
      <h3 id="situation-instructions" className="panel-section-title">{SITUATION_COPY.instructionsTitle}</h3>
      <table className="fact-table situation-instructions" aria-labelledby="situation-instructions">
        <thead>
          <tr>
            <th scope="col">{SITUATION_COPY.instruction}</th>
            <th scope="col">{SITUATION_COPY.asset}</th>
            <th scope="col">{SITUATION_COPY.issued}</th>
            <th scope="col">{SITUATION_COPY.effectiveUntil}</th>
            <th scope="col">{SITUATION_COPY.source}</th>
          </tr>
        </thead>
        <tbody>
          {instructions.map((instruction) => (
            <tr key={instruction.id}>
              <th scope="row">{instruction.text}</th>
              <td data-label={SITUATION_COPY.asset}>{instruction.asset}</td>
              <td data-label={SITUATION_COPY.issued}>{formatDateTime(instruction.issuedAt)}</td>
              <td data-label={SITUATION_COPY.effectiveUntil}>
                {instruction.effectiveUntil ? formatDateTime(instruction.effectiveUntil) : SITUATION_COPY.untilFurtherNotice}
              </td>
              <td data-label={SITUATION_COPY.source}>{instruction.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EditLog({ edits, facts }: { edits: OperatorEdit[]; facts: SituationFact[] }) {
  return (
    <div className="situation-group">
      <h3 className="panel-section-title">{SITUATION_COPY.editsTitle}</h3>
      <ol className="situation-edit-log">
        {edits.map((edit, index) => {
          const fact = facts.find((item) => item.id === edit.factId);
          const unit = fact?.unit ?? null;
          return (
            <li key={`${edit.factId}-${edit.at}-${index}`}>
              <span className="situation-edit-label">{fact?.label ?? edit.label}</span>
              {': '}
              <span className="situation-value">{valueText(edit.from, unit)} → {valueText(edit.to, unit)}</span>
              <span className="situation-edit-time">{formatDateTime(edit.at)}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// Section 3: the facts the assessment used, grouped by the families of the
// binding conditions, plus the instructions already in force and every
// operator edit. Any edit makes the assessment stale until it is rerun.
// Missing facts wait behind one disclosure so they do not dominate.
function SituationTable({ facts, conditions, activeInstructions, edits, onEdit }: Props) {
  const [missingOpen, setMissingOpen] = useState(false);
  const families = new Set<FactGroup>(['general', ...conditions.map((condition) => familyOf(condition.scenarioId))]);
  const groups = GROUP_ORDER
    .filter((group) => families.has(group))
    .map((group) => ({ group, rows: facts.filter((fact) => fact.family === group) }))
    .filter(({ rows }) => rows.length > 0);
  const inScope = groups.flatMap(({ rows }) => rows);
  const shown = groups
    .map(({ group, rows }) => ({ group, rows: rows.filter((fact) => !isHidden(fact, edits)) }))
    .filter(({ rows }) => rows.length > 0);
  const hidden = groups
    .map(({ group, rows }) => ({ group, rows: rows.filter((fact) => isHidden(fact, edits)) }))
    .filter(({ rows }) => rows.length > 0);
  const hiddenCount = hidden.reduce((total, { rows }) => total + rows.length, 0);

  return (
    <section className="card situation-table" aria-labelledby="situation-heading">
      <div className="panel-header">
        <h2 id="situation-heading" className="panel-title">{SITUATION_COPY.title}</h2>
        {inScope.length > 0 && <span className="panel-meta">{stateSummary(inScope)}</span>}
      </div>
      <p className="situation-intro">{SITUATION_COPY.intro}</p>
      {groups.length === 0 && <p className="situation-empty">{SITUATION_COPY.noFacts}</p>}
      {groups.length > 0 && shown.length === 0 && <p className="situation-empty">{SITUATION_COPY.noSupplied}</p>}
      {shown.map(({ group, rows }) => (
        <FactGroupTable key={group} group={group} facts={rows} edits={edits} onEdit={onEdit} idPrefix="situation" />
      ))}
      {hiddenCount > 0 && (
        <details
          className="disclosure situation-missing"
          onToggle={(event) => setMissingOpen(event.currentTarget.open)}
        >
          <summary>{missingOpen ? SITUATION_COPY.hideMissing(hiddenCount) : SITUATION_COPY.showMissing(hiddenCount)}</summary>
          {hidden.map(({ group, rows }) => (
            <FactGroupTable key={group} group={group} facts={rows} edits={edits} onEdit={onEdit} idPrefix="situation-missing" />
          ))}
        </details>
      )}
      <InstructionList instructions={activeInstructions} />
      {edits.length > 0 && <EditLog edits={edits} facts={facts} />}
    </section>
  );
}

export default SituationTable;

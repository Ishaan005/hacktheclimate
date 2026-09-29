import { useState } from 'react';
import type { FormEvent } from 'react';
import { DATA_STATUS_LABEL, ORIGIN_LABEL, STALE_NOTE } from '../../decision/copy/shared';
import { FACT_GROUP_LABEL, SITUATION_COPY } from '../../decision/copy/situation';
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
  stale: boolean;
  onEdit: (id: string, value: number | string | null) => void;
  onRerun: () => void;
};

type FactGroup = ScenarioFamily | 'general';

const GROUP_ORDER: FactGroup[] = ['general', 'transmission', 'high_frequency_minimum_generation', 'snsp'];

// Only current may look neutral; anything uncertain is amber.
const STATE_TONE: Record<DataStatus, string> = {
  current: 'chip-neutral',
  stale: 'chip-unknown',
  missing: 'chip-unknown',
  conflicting: 'chip-unknown',
  modeled: 'chip-unknown',
};

// Null means not supplied: show Missing, never zero.
function valueText(value: number | string | null, unit: string | null): string {
  if (value === null) return SITUATION_COPY.missing;
  if (!unit) return String(value);
  return unit === '%' ? `${value}%` : `${value} ${unit}`;
}

function provenanceText(fact: SituationFact): string {
  if (fact.state === 'missing' && fact.missingReason) return fact.missingReason;
  if (fact.state === 'modeled' && fact.timestamp) return formatDateTime(fact.timestamp);
  const parts = [fact.source, fact.timestamp ? formatDateTime(fact.timestamp) : null].filter(Boolean);
  return parts.length ? parts.join(' · ') : SITUATION_COPY.noSource;
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
  const numeric = typeof fact.value === 'number' || ['MW', 'MVA', 'MWh', 'Hz', '%', 'units', 'min', 'seconds', 'hours', 'MW/min'].includes(fact.unit ?? '');
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
      <button type="button" className="situation-link" onClick={onCancel}>{SITUATION_COPY.cancel}</button>
    </form>
  );
}

type TableProps = {
  group: FactGroup;
  facts: SituationFact[];
  edits: OperatorEdit[];
  onEdit: Props['onEdit'];
};

function FactGroupTable({ group, facts, edits, onEdit }: TableProps) {
  const [editing, setEditing] = useState<string | null>(null);
  const headingId = `situation-${group}`;
  return (
    <div className="fact-section">
      <h3 id={headingId} className="fact-section-title">{FACT_GROUP_LABEL[group]}</h3>
      <table className="fact-table situation-facts" aria-labelledby={headingId}>
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
            const edited = firstEdit !== undefined || fact.editedFrom !== null;
            const previous = firstEdit ? firstEdit.from : fact.editedFrom;
            return (
              <tr key={fact.id} className={missing ? 'fact-missing' : undefined}>
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
                      <span className="mono">{valueText(fact.value, fact.unit)}</span>
                      {edited && (
                        <span className="cell-note situation-edited">
                          {SITUATION_COPY.editedWas(valueText(previous, fact.unit))}
                        </span>
                      )}
                      <span className="cell-note">{provenanceText(fact)}</span>
                    </div>
                  )}
                </td>
                <td data-label={SITUATION_COPY.origin}>{ORIGIN_LABEL[fact.origin]}</td>
                <td data-label={SITUATION_COPY.state}>
                  <span className={`chip ${STATE_TONE[fact.state]}`}>{DATA_STATUS_LABEL[fact.state]}</span>
                  {fact.state === 'conflicting' && fact.conflictNote && (
                    <span className="cell-note situation-conflict">{fact.conflictNote}</span>
                  )}
                </td>
                <td>
                  {canEdit(fact) && editing !== fact.id && (
                    <button
                      type="button"
                      className={missing ? 'button-secondary' : 'situation-link'}
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
  return (
    <div className="fact-section">
      <h3 id="situation-instructions" className="fact-section-title">{SITUATION_COPY.instructionsTitle}</h3>
      <table className="fact-table" aria-labelledby="situation-instructions">
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
    <div className="fact-section">
      <h3 className="fact-section-title">{SITUATION_COPY.editsTitle}</h3>
      <ol className="situation-edit-log">
        {edits.map((edit, index) => {
          const fact = facts.find((item) => item.id === edit.factId);
          const unit = fact?.unit ?? null;
          return (
            <li key={`${edit.factId}-${edit.at}-${index}`}>
              <span className="situation-edit-label">{fact?.label ?? edit.factId}</span>
              {': '}
              <span className="mono">{valueText(edit.from, unit)} → {valueText(edit.to, unit)}</span>
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
function SituationTable({ facts, conditions, activeInstructions, edits, stale, onEdit, onRerun }: Props) {
  const families = new Set<FactGroup>(['general', ...conditions.map((condition) => familyOf(condition.scenarioId))]);
  const groups = GROUP_ORDER
    .filter((group) => families.has(group))
    .map((group) => ({ group, rows: facts.filter((fact) => fact.family === group && (fact.value !== null || fact.state === 'conflicting')) }))
    .filter(({ rows }) => rows.length > 0);

  if (!groups.length && !activeInstructions.length && !edits.length && !stale) return null;

  return (
    <section className="card situation-table" aria-labelledby="situation-heading">
      <h2 id="situation-heading" className="card-kicker">{SITUATION_COPY.title}</h2>
      <p className="situation-intro">{SITUATION_COPY.intro}</p>
      {stale && (
        <div className="situation-stale" role="status">
          <p>{STALE_NOTE}</p>
          <button type="button" className="button-primary" onClick={onRerun}>{SITUATION_COPY.rerun}</button>
        </div>
      )}
      {groups.map(({ group, rows }) => (
        <FactGroupTable key={group} group={group} facts={rows} edits={edits} onEdit={onEdit} />
      ))}
      {activeInstructions.length > 0 && <InstructionList instructions={activeInstructions} />}
      {edits.length > 0 && <EditLog edits={edits} facts={facts} />}
    </section>
  );
}

export default SituationTable;

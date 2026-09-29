import { useState } from 'react';
import type { FormEvent } from 'react';
import { clarificationQuestions, isMissing, missingRequiredFacts, readyForEvaluation, reviewSections } from '../case';
import { EXTRACTION_LABEL, FACT_SOURCE_LABEL, FACT_STATUS_LABEL, REVIEW_COPY, WORKSPACE_COPY } from '../copy';
import { formatDateTime } from '../format';
import type { Extraction } from '../api';
import type { Fact, FactStatus, FactValue, OperatorCase, ReviewRow, ReviewSection } from '../case';
import StatusMessage from './StatusMessage';
import './CaseReview.css';

type Props = {
  operatorCase: OperatorCase;
  extraction: Extraction;
  onCorrect: (id: string, value: FactValue, unit: string | null) => void;
  onEvaluate: () => void;
  onCancel: () => void;
};

// Only verified is green. Inferred and forecast values are not checked, so
// they must not look confirmed.
const STATUS_TONE: Record<FactStatus, string> = {
  operator_supplied: 'chip-neutral',
  system_inferred: 'chip-advisory',
  forecast: 'chip-advisory',
  verified: 'chip-within_modelled_limit',
  corrected: 'chip-neutral',
  stale: 'chip-unknown',
  unknown: 'chip-unknown',
};

// Source and time sit on one line under the value to keep the table narrow.
function provenanceText(fact: Fact | null): string | null {
  if (!fact) return null;
  const parts = [
    fact.source ? FACT_SOURCE_LABEL[fact.source] : null,
    fact.sourceName,
    fact.asOf ? formatDateTime(fact.asOf) : null,
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : null;
}

function valueText(fact: Fact | null): string {
  if (!fact || fact.value === null) return REVIEW_COPY.unknownValue;
  return fact.unit ? `${fact.value} ${fact.unit}` : String(fact.value);
}

type EditorProps = {
  row: ReviewRow;
  onSave: (value: FactValue) => void;
  onCancel: () => void;
};

// Inline editor: the control matches the fact, so a number cannot be saved
// as text and a choice only offers its options.
function FactEditor({ row, onSave, onCancel }: EditorProps) {
  const { definition, fact } = row;
  const [draft, setDraft] = useState(fact && !isMissing(fact) && definition.kind !== 'choice' ? String(fact.value) : '');
  const inputId = `edit-${row.id}`;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    onSave(definition.kind === 'number' ? Number(draft) : draft.trim());
  }

  const numberInvalid = definition.kind === 'number' && draft !== ''
    && (!Number.isFinite(Number(draft))
      || (definition.min !== undefined && Number(draft) < definition.min)
      || (definition.max !== undefined && Number(draft) > definition.max));

  return (
    <form className="fact-editor" onSubmit={submit}>
      <label htmlFor={inputId} className="visually-hidden">{definition.label}</label>
      {definition.kind === 'choice' && definition.options ? (
        <select id={inputId} className="input" value={draft} onChange={(event) => setDraft(event.target.value)}>
          <option value="" disabled>{REVIEW_COPY.unknownValue}</option>
          {definition.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      ) : (
        <input
          id={inputId}
          className="input"
          type={definition.kind === 'number' ? 'number' : 'text'}
          min={definition.min}
          max={definition.max}
          step={definition.step}
          value={draft}
          aria-invalid={numberInvalid || undefined}
          onChange={(event) => setDraft(event.target.value)}
        />
      )}
      {definition.unit && <span className="fact-unit">{definition.unit}</span>}
      <button type="submit" className="button-secondary" disabled={!draft.trim() || numberInvalid}>{REVIEW_COPY.save}</button>
      <button type="button" className="button-ghost" onClick={onCancel}>{REVIEW_COPY.cancel}</button>
    </form>
  );
}

function FactTable({ section, onCorrect }: { section: ReviewSection; onCorrect: Props['onCorrect'] }) {
  const [editing, setEditing] = useState<string | null>(null);
  const headingId = `review-${section.scope}`;
  return (
    <div className="fact-section">
      <h3 id={headingId} className="fact-section-title">{section.title}</h3>
      <table className="fact-table" aria-labelledby={headingId}>
        <thead>
          <tr>
            <th scope="col">{REVIEW_COPY.fact}</th>
            <th scope="col">{REVIEW_COPY.value}</th>
            <th scope="col">{REVIEW_COPY.status}</th>
            <th scope="col"><span className="visually-hidden">{REVIEW_COPY.edit}</span></th>
          </tr>
        </thead>
        <tbody>
          {section.rows.map((row) => {
            const { fact, definition } = row;
            const status: FactStatus = fact ? fact.status : 'unknown';
            const provenance = provenanceText(fact);
            const missingRow = isMissing(fact ?? undefined);
            const action = missingRow ? REVIEW_COPY.add : REVIEW_COPY.edit;
            return (
              <tr key={row.id} className={missingRow ? 'fact-missing' : undefined}>
                <th scope="row">
                  {definition.label}
                  {!row.required && <span className="fact-optional"> ({REVIEW_COPY.optional})</span>}
                </th>
                <td data-label={REVIEW_COPY.value}>
                  {editing === row.id ? (
                    <FactEditor
                      row={row}
                      onSave={(value) => {
                        onCorrect(row.id, value, definition.unit);
                        setEditing(null);
                      }}
                      onCancel={() => setEditing(null)}
                    />
                  ) : (
                    <div>
                      <span className="mono">{valueText(fact)}</span>
                      {provenance && <span className="cell-note">{provenance}</span>}
                    </div>
                  )}
                </td>
                <td data-label={REVIEW_COPY.status}><span className={`chip ${STATUS_TONE[status]}`}>{FACT_STATUS_LABEL[status]}</span></td>
                <td>
                  {editing !== row.id && (
                    <button
                      type="button"
                      className={missingRow ? 'button-secondary' : 'button-ghost'}
                      aria-label={`${action} ${definition.label}`}
                      onClick={() => setEditing(row.id)}
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

// Issue 04–06 review step: every fact the tool will use, with its source,
// time and status, and an edit control per row. Missing facts are filled in
// the table itself and listed most-blocking first. Nothing is evaluated while
// a required fact is missing.
function CaseReview({ operatorCase, extraction, onCorrect, onEvaluate, onCancel }: Props) {
  const missing = missingRequiredFacts(operatorCase);
  const questions = clarificationQuestions(missing);
  const ready = readyForEvaluation(operatorCase);
  return (
    <section className="card case-review" aria-labelledby="review-heading">
      <h2 id="review-heading" className="card-kicker">
        {REVIEW_COPY.title}
        <span className="chip chip-neutral">{EXTRACTION_LABEL[extraction]}</span>
      </h2>
      <p className="case-review-intro">{REVIEW_COPY.intro}</p>
      <p className="clarify-description"><q>{operatorCase.originalText}</q></p>
      {reviewSections(operatorCase).map((section) => (
        <FactTable key={section.scope} section={section} onCorrect={onCorrect} />
      ))}
      {!ready && (
        <StatusMessage
          tone="unavailable"
          title={REVIEW_COPY.stoppedTitle}
          consequence={REVIEW_COPY.stoppedConsequence}
          items={questions.map((question) => question.prompt)}
        />
      )}
      <div className="case-review-actions">
        {ready && <button type="button" className="button-primary" onClick={onEvaluate}>{REVIEW_COPY.evaluate}</button>}
        <button type="button" className="button-ghost" onClick={onCancel}>{WORKSPACE_COPY.clarifyCancel}</button>
      </div>
    </section>
  );
}

export default CaseReview;

import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { SEARCH_COPY } from '../../decision/copy/search';
import { jurisdictionOf, matchDescription, suggestionByKey } from '../../decision/scope';
import type { Suggestion } from '../../decision/scope';
import type { BindingCondition, CauseUnknown } from '../../decision/types';
import AutoGrowTextarea from '../AutoGrowTextarea';
import LimitingProblemReview from './LimitingProblemReview';
import SuggestionList from './SuggestionList';
import './SituationSearch.css';

type Props = {
  onAssess: (description: string, conditions: BindingCondition[]) => void;
  busy?: boolean;
};

type Row = { id: string; condition: BindingCondition };

// A new condition carries only what the suggestion itself says. The
// operator records the rest; the hook confirms it at assessment.
function conditionFrom(suggestion: Suggestion): BindingCondition {
  return {
    scenarioId: suggestion.scenarioId,
    situationKey: suggestion.key,
    reach: null,
    limitingAsset: null,
    outageType: null,
    timeSetting: null,
    snspDrivers: [],
    jurisdiction: jurisdictionOf(suggestion.key),
    confirmedByOperator: false,
  };
}

// Section 2 of the brief: find the situation. The operator picks a
// suggestion or describes it; the app shows what it thinks is limiting; the
// operator reviews every limit before assessment. Cause unknown is an intake
// state: it never goes to assessment with no condition.
function SituationSearch({ onAssess, busy = false }: Props) {
  const [description, setDescription] = useState('');
  const [rows, setRows] = useState<Row[]>([]);
  const [causeUnknown, setCauseUnknown] = useState<CauseUnknown | null>(null);
  const [adding, setAdding] = useState(false);
  const nextId = useRef(0);

  function makeRow(suggestion: Suggestion): Row {
    nextId.current += 1;
    return { id: `limit-${nextId.current}`, condition: conditionFrom(suggestion) };
  }

  function find(event: FormEvent) {
    event.preventDefault();
    if (!description.trim()) return;
    const result = matchDescription(description);
    setAdding(false);
    if (result.kind === 'cause_unknown') {
      setRows([]);
      setCauseUnknown({ reason: result.reason, factsNeeded: result.factsNeeded });
      return;
    }
    setCauseUnknown(null);
    setRows(result.suggestions.map(makeRow));
  }

  function pick(suggestion: Suggestion) {
    setCauseUnknown(null);
    setAdding(false);
    setRows((current) => (current.some((row) => row.condition.situationKey === suggestion.key)
      ? current
      : [...current, makeRow(suggestion)]));
  }


  function remove(id: string) {
    setRows((current) => current.filter((row) => row.id !== id));
  }

  function assess() {
    if (!rows.length || busy) return;
    const conditions = rows.map((row) => row.condition);
    // A picked suggestion without typed text still sends a readable description.
    const text = description.trim()
      || conditions.map((condition) => suggestionByKey(condition.situationKey)?.text ?? '').filter(Boolean).join(' ');
    onAssess(text, conditions);
  }

  const reviewing = rows.length > 0;
  const showSuggestions = !reviewing || adding;

  return (
    <section className="situation-search">
      <form className="search-bar" onSubmit={find}>
        <label htmlFor="situation-search-input" className="search-bar-label">{SEARCH_COPY.label}</label>
        <p id="situation-search-hint" className="search-bar-hint">{SEARCH_COPY.hint}</p>
        <div className="search-bar-row">
          <AutoGrowTextarea
            id="situation-search-input"
            aria-describedby="situation-search-hint"
            value={description}
            onChange={setDescription}
            placeholder={SEARCH_COPY.placeholder}
          />
          <button type="submit" className="button-secondary" disabled={!description.trim() || busy}>
            {SEARCH_COPY.find}
          </button>
        </div>
      </form>

      {causeUnknown && (
        <div className="search-intake" role="status">
          <h3 className="search-intake-title">{SEARCH_COPY.causeUnknownHeading}</h3>
          <p className="search-intake-reason">{causeUnknown.reason}</p>
          <p className="field-label">{SEARCH_COPY.factsNeededLabel}</p>
          <ul className="search-intake-facts">
            {causeUnknown.factsNeeded.map((fact) => <li key={fact}>{fact}</li>)}
          </ul>
          <p className="field-hint">{SEARCH_COPY.causeUnknownNext}</p>
        </div>
      )}

      {reviewing && (
        <div className="search-review">
          <h3 className="search-review-title">{SEARCH_COPY.reviewHeading}</h3>
          <p className="field-hint">{SEARCH_COPY.reviewHint}</p>
          <p className="field-hint">{SEARCH_COPY.feedNote}</p>
          <ul className="search-review-list">
            {rows.map((row) => (
              <LimitingProblemReview
                key={row.id}
                rowId={row.id}
                condition={row.condition}
                onRemove={() => remove(row.id)}
              />
            ))}
          </ul>
          <div className="search-review-actions">
            <button type="button" className="button-secondary" aria-expanded={adding} onClick={() => setAdding((open) => !open)}>
              {adding ? SEARCH_COPY.hideSuggestions : SEARCH_COPY.addAnother}
            </button>
            <button type="button" className="button-primary" disabled={busy} onClick={assess}>
              {busy ? SEARCH_COPY.assessing : SEARCH_COPY.assess}
            </button>
          </div>
        </div>
      )}

      {showSuggestions && (
        <SuggestionList exclude={rows.map((row) => row.condition.situationKey ?? '')} onPick={pick} />
      )}
    </section>
  );
}

export default SituationSearch;

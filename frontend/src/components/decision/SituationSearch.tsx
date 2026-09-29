import { useState } from 'react';
import type { FormEvent } from 'react';
import { SEARCH_COPY } from '../../decision/copy/search';
import type { Suggestion } from '../../decision/scope';
import AutoGrowTextarea from '../AutoGrowTextarea';
import SuggestionList from './SuggestionList';
import './SituationSearch.css';

type Props = {
  onAssess: (description: string) => void;
  busy?: boolean;
};

// Section 2 of the brief: the operator describes the situation in their own
// words and assesses it. The assessment works out what is limiting from the
// text; the result shows it, or Cause unknown with the facts it needs.
// Example situations from the locked scope only fill the text box.
function SituationSearch({ onAssess, busy = false }: Props) {
  const [description, setDescription] = useState('');
  const ready = description.trim().length > 0 && !busy;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!ready) return;
    onAssess(description.trim());
  }

  function pick(suggestion: Suggestion) {
    setDescription((current) => (current.trim() ? `${current.trim()} ${suggestion.text}` : suggestion.text));
  }

  return (
    <section className="situation-search">
      <form className="search-bar" onSubmit={submit}>
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
          <button type="submit" className="button-primary" disabled={!ready}>
            {busy ? SEARCH_COPY.assessing : SEARCH_COPY.assess}
          </button>
        </div>
        {/* Examples sit inside the card; picking one only fills the box. */}
        <details className="disclosure search-examples">
          <summary>{SEARCH_COPY.examplesSummary}</summary>
          <SuggestionList exclude={[]} onPick={pick} />
        </details>
      </form>
    </section>
  );
}

export default SituationSearch;

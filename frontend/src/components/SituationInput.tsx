import { useState } from 'react';
import type { FormEvent } from 'react';
import { REVIEW_COPY, WORKSPACE_COPY } from '../copy';

type Props = {
  onSubmit: (description: string, comparison: string | null) => void;
  initialValue?: string;
};

// Stage 1 of the intent flow: the operator types the situation and, if they
// want, an action of their own or a second situation to compare. A later
// alert feed can pre-populate `initialValue` instead.
function SituationInput({ onSubmit, initialValue = '' }: Props) {
  const [description, setDescription] = useState(initialValue);
  const [comparison, setComparison] = useState('');

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit(description, comparison.trim() || null);
  }

  return (
    <form className="situation" onSubmit={submit}>
      <label htmlFor="situation-input" className="situation-label">{WORKSPACE_COPY.situationLabel}</label>
      <p id="situation-hint" className="situation-hint">{WORKSPACE_COPY.situationHint}</p>
      <div className="situation-row">
        <input
          id="situation-input"
          type="text"
          aria-describedby="situation-hint"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder={WORKSPACE_COPY.situationPlaceholder}
        />
        <button type="submit" className="button-primary" disabled={!description.trim()}>
          {WORKSPACE_COPY.situationSubmit}
        </button>
      </div>
      <label htmlFor="comparison-input" className="situation-label situation-label-secondary">{REVIEW_COPY.comparisonLabel}</label>
      <p id="comparison-hint" className="situation-hint">{REVIEW_COPY.comparisonHint}</p>
      <input
        id="comparison-input"
        type="text"
        aria-describedby="comparison-hint"
        value={comparison}
        onChange={(event) => setComparison(event.target.value)}
        placeholder={REVIEW_COPY.comparisonPlaceholder}
      />
    </form>
  );
}

export default SituationInput;

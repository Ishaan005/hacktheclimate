import { useState } from 'react';
import type { FormEvent } from 'react';
import { WORKSPACE_COPY } from '../copy';
import AutoGrowTextarea from './AutoGrowTextarea';

type Props = {
  onSubmit: (description: string) => void;
  initialValue?: string;
};

// Stage 1 of the intent flow: the operator types the situation. A later
// alert feed can pre-populate `initialValue` instead.
function SituationInput({ onSubmit, initialValue = '' }: Props) {
  const [description, setDescription] = useState(initialValue);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!description.trim()) return;
    onSubmit(description);
  }

  return (
    <form className="situation" onSubmit={submit}>
      <label htmlFor="situation-input" className="situation-label">{WORKSPACE_COPY.situationLabel}</label>
      <p id="situation-hint" className="situation-hint">{WORKSPACE_COPY.situationHint}</p>
      <div className="situation-row">
        <AutoGrowTextarea
          id="situation-input"
          aria-describedby="situation-hint"
          value={description}
          onChange={setDescription}
          placeholder={WORKSPACE_COPY.situationPlaceholder}
        />
        <button type="submit" className="button-primary" disabled={!description.trim()}>
          {WORKSPACE_COPY.situationSubmit}
        </button>
      </div>
    </form>
  );
}

export default SituationInput;

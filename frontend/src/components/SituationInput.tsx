import { useLayoutEffect, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent, TextareaHTMLAttributes } from 'react';
import { WORKSPACE_COPY } from '../copy';

type Props = {
  onSubmit: (description: string) => void;
  initialValue?: string;
};

type AutoGrowProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange' | 'value'> & {
  value: string;
  onChange: (value: string) => void;
};

// Grows with its content up to the CSS max-height, then scrolls. Enter
// submits the form; Shift+Enter adds a new line.
function AutoGrowTextarea({ value, onChange, ...rest }: AutoGrowProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${element.scrollHeight + element.offsetHeight - element.clientHeight}px`;
  }, [value]);
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }
  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={onKeyDown}
      {...rest}
    />
  );
}

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

import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { initialAnswer, isEmptyAnswer, toAnswers, validateAnswer } from '../clarification';
import { WORKSPACE_COPY } from '../copy';
import type {
  ClarificationAnswer,
  ClarificationAnswerValue,
  ClarificationQuestion,
  ClarificationRequest,
  MultiChoiceQuestion,
  NumberQuestion,
  SingleChoiceQuestion,
  TextQuestion,
} from '../types';
import './ClarificationForm.css';

type Props = {
  clarification: ClarificationRequest;
  description: string;
  round: number;
  onSubmit: (answers: ClarificationAnswer[]) => void;
  onCancel: () => void;
};

type ControlProps<Q extends ClarificationQuestion> = {
  question: Q;
  value: ClarificationAnswerValue;
  onChange: (value: ClarificationAnswerValue) => void;
  inputId: string;
  describedBy: string | undefined;
  invalid: boolean;
};

function TextControl({ question, value, onChange, inputId, describedBy, invalid }: ControlProps<TextQuestion>) {
  return (
    <textarea
      id={inputId}
      className="input clarify-textarea"
      rows={2}
      value={typeof value === 'string' ? value : ''}
      placeholder={question.placeholder ?? undefined}
      maxLength={question.maxLength ?? undefined}
      aria-describedby={describedBy}
      aria-invalid={invalid || undefined}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

function SingleChoiceControl({ question, value, onChange, inputId, describedBy, invalid }: ControlProps<SingleChoiceQuestion>) {
  return (
    <div className="clarify-options" role="radiogroup" aria-describedby={describedBy} aria-invalid={invalid || undefined}>
      {question.options.map((option, index) => (
        <label key={option.value} className="clarify-option">
          <input
            // The first option carries the group id so errors can focus it.
            id={index === 0 ? inputId : undefined}
            type="radio"
            name={inputId}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  );
}

function MultiChoiceControl({ question, value, onChange, inputId, describedBy, invalid }: ControlProps<MultiChoiceQuestion>) {
  const selected = Array.isArray(value) ? value : [];
  function toggle(optionValue: string) {
    onChange(selected.includes(optionValue) ? selected.filter((item) => item !== optionValue) : [...selected, optionValue]);
  }
  return (
    <div className="clarify-options" role="group" aria-describedby={describedBy} aria-invalid={invalid || undefined}>
      {question.options.map((option, index) => (
        <label key={option.value} className="clarify-option">
          <input
            id={index === 0 ? inputId : undefined}
            type="checkbox"
            value={option.value}
            checked={selected.includes(option.value)}
            onChange={() => toggle(option.value)}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  );
}

// Slider plus number field, kept in step. Unset until the operator moves or
// types: a resting slider position is not an answer.
function NumberControl({ question, value, onChange, inputId, describedBy, invalid }: ControlProps<NumberQuestion>) {
  const current = typeof value === 'number' ? value : null;
  const resting = current ?? question.defaultValue ?? question.min;
  const unit = question.unit ? ` ${question.unit}` : '';
  return (
    <div className="clarify-number">
      <input
        type="range"
        className="clarify-range"
        min={question.min}
        max={question.max}
        step={question.step}
        value={resting}
        aria-label={`${question.prompt} (slider)`}
        aria-valuetext={current === null ? WORKSPACE_COPY.clarifyNotSet : `${current}${unit}`}
        aria-describedby={describedBy}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <span className="clarify-number-field">
        <input
          id={inputId}
          type="number"
          className="input mono"
          min={question.min}
          max={question.max}
          step={question.step}
          value={current ?? ''}
          placeholder={WORKSPACE_COPY.clarifyNotSet}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
          onChange={(event) => onChange(event.target.value === '' ? null : Number(event.target.value))}
        />
        {question.unit && <span className="clarify-unit">{question.unit}</span>}
      </span>
      <span className="clarify-range-limits mono" aria-hidden="true">
        <span>{question.min}{unit}</span>
        <span>{question.max}{unit}</span>
      </span>
      {current !== null && !question.required && (
        <button type="button" className="button-ghost" onClick={() => onChange(null)}>
          {WORKSPACE_COPY.clarifyClear}
        </button>
      )}
    </div>
  );
}

function QuestionControl(props: ControlProps<ClarificationQuestion>) {
  const { question } = props;
  switch (question.kind) {
    case 'text':
      return <TextControl {...props} question={question} />;
    case 'single_choice':
      return <SingleChoiceControl {...props} question={question} />;
    case 'multi_choice':
      return <MultiChoiceControl {...props} question={question} />;
    case 'number':
      return <NumberControl {...props} question={question} />;
  }
}

// Choice groups use fieldset and legend; single controls use a label.
function QuestionField({
  question,
  value,
  error,
  onChange,
}: {
  question: ClarificationQuestion;
  value: ClarificationAnswerValue;
  error: string | null;
  onChange: (value: ClarificationAnswerValue) => void;
}) {
  const inputId = `clarify-${question.id}`;
  const helpId = question.helpText ? `${inputId}-help` : null;
  const errorId = error ? `${inputId}-error` : null;
  const describedBy = [helpId, errorId].filter(Boolean).join(' ') || undefined;
  const grouped = question.kind === 'single_choice' || question.kind === 'multi_choice';
  const title = (
    <>
      {question.prompt}
      {!question.required && <span className="clarify-optional"> ({WORKSPACE_COPY.clarifyOptional})</span>}
    </>
  );
  const body = (
    <>
      {question.helpText && <p id={helpId ?? undefined} className="field-hint">{question.helpText}</p>}
      <QuestionControl
        question={question}
        value={value}
        onChange={onChange}
        inputId={inputId}
        describedBy={describedBy}
        invalid={Boolean(error)}
      />
      {error && <p id={errorId ?? undefined} className="field-hint field-hint-error">{error}</p>}
    </>
  );
  if (grouped) {
    return (
      <fieldset className="clarify-question">
        <legend className="field-label">{title}</legend>
        {body}
      </fieldset>
    );
  }
  return (
    <div className="clarify-question">
      <label htmlFor={inputId} className="field-label">{title}</label>
      {body}
    </div>
  );
}

// Follow-up questions from the solver, one at a time so the operator is not
// faced with a wall of fields. Answers are kept when stepping back, and all
// of them go to the solver together after the last question. No action is
// shown until the solver has enough detail to return one.
function ClarificationForm({ clarification, description, round, onSubmit, onCancel }: Props) {
  const { questions } = clarification;
  const [values, setValues] = useState<Record<string, ClarificationAnswerValue>>(() =>
    Object.fromEntries(questions.map((question) => [question.id, initialAnswer(question)])),
  );
  const [step, setStep] = useState(0);
  const [showError, setShowError] = useState(false);
  const movedRef = useRef(false);
  const question = questions[step];
  const value = values[question.id] ?? null;
  const error = validateAnswer(question, value);
  const last = step === questions.length - 1;

  // Move focus to the new question after Next or Back, not on first render.
  useEffect(() => {
    if (!movedRef.current) return;
    document.getElementById(`clarify-${questions[step].id}`)?.focus();
  }, [step, questions]);

  function goTo(next: number) {
    movedRef.current = true;
    setShowError(false);
    setStep(next);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (error) {
      setShowError(true);
      document.getElementById(`clarify-${question.id}`)?.focus();
      return;
    }
    if (last) onSubmit(toAnswers(questions, values));
    else goTo(step + 1);
  }

  const skipping = !question.required && isEmptyAnswer(value);
  const advanceLabel = last ? WORKSPACE_COPY.clarifySubmit : skipping ? WORKSPACE_COPY.clarifySkip : WORKSPACE_COPY.clarifyNext;

  return (
    <section className="card clarify" aria-labelledby="clarify-heading">
      <h2 id="clarify-heading" className="card-kicker">
        {WORKSPACE_COPY.clarifyTitle}
        {round > 1 && <span className="chip chip-neutral">{WORKSPACE_COPY.clarifyRound} {round}</span>}
      </h2>
      <p className="clarify-reason">{clarification.reason}</p>
      <p className="clarify-description">
        {WORKSPACE_COPY.clarifyDescribed}: <q>{description}</q>
      </p>
      <form className="clarify-form" onSubmit={submit} noValidate>
        {questions.length > 1 && (
          <p className="clarify-progress" aria-live="polite">
            {WORKSPACE_COPY.clarifyQuestion} {step + 1} {WORKSPACE_COPY.clarifyOf} {questions.length}
          </p>
        )}
        <QuestionField
          key={question.id}
          question={question}
          value={value}
          error={showError ? error : null}
          onChange={(next) => setValues((current) => ({ ...current, [question.id]: next }))}
        />
        <div className="clarify-actions">
          <button type="submit" className="button-primary">{advanceLabel}</button>
          {step > 0 && (
            <button type="button" className="button-secondary" onClick={() => goTo(step - 1)}>
              {WORKSPACE_COPY.clarifyBack}
            </button>
          )}
          <button type="button" className="button-ghost" onClick={onCancel}>{WORKSPACE_COPY.clarifyCancel}</button>
        </div>
      </form>
    </section>
  );
}

export default ClarificationForm;

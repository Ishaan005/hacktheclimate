import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AssistantApp from './AssistantApp';
import * as api from './api';
import { STORAGE_KEY } from './caseStore';
import { newCase, SITUATION_FACTS } from './case';
import { REVIEW_COPY, WORKSPACE_COPY } from './copy';
import { illustrativeClarification } from './fixtures/illustrativeClarification';
import { illustrativeScenarios } from './fixtures/illustrativeScenarios';
import { MAX_CLARIFICATION_ROUNDS } from './useSituationSolver';

const [thermal] = illustrativeScenarios;

// These tests cover the solver's own follow-up questions, which come after
// the fact review. Intake returns a case with every required fact known so
// the review can go straight to evaluation.
function reviewedCase(description: string) {
  const facts = Object.fromEntries(SITUATION_FACTS.map((definition) => [definition.key, {
    key: definition.key, value: 1, unit: definition.unit, status: 'verified' as const, source: 'forecast' as const,
    sourceName: 'test', asOf: '2026-09-29T06:00:00Z', history: [],
  }]));
  return { ...newCase(description, '2026-09-29T08:00:00Z'), scenarios: ['local_network_constraint' as const], facts };
}

beforeEach(() => {
  vi.spyOn(api, 'startCase').mockImplementation(async (description) => ({ operatorCase: reviewedCase(description), extraction: 'fixture' }));
});

async function submitSituation(value: string) {
  fireEvent.change(screen.getByLabelText(WORKSPACE_COPY.situationLabel), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: WORKSPACE_COPY.situationSubmit }));
  fireEvent.click(await screen.findByRole('button', { name: REVIEW_COPY.evaluate }));
}

async function openQuestions() {
  render(<AssistantApp />);
  await submitSituation('there is a problem');
  return screen.findByRole('region', { name: WORKSPACE_COPY.clarifyTitle });
}

afterEach(() => vi.restoreAllMocks());

function click(form: HTMLElement, name: string) {
  fireEvent.click(within(form).getByRole('button', { name }));
}

describe('solver follow-up questions', () => {
  it('asks one question at a time for a vague description', async () => {
    const form = await openQuestions();
    expect(within(form).getByText(illustrativeClarification.reason)).toBeInTheDocument();
    expect(within(form).getByText('Question 1 of 4')).toBeInTheDocument();
    expect(within(form).getByRole('radiogroup')).toBeInTheDocument();
    expect(within(form).queryByRole('checkbox')).not.toBeInTheDocument();
    expect(within(form).queryByRole('slider')).not.toBeInTheDocument();
    expect(within(form).queryByRole('button', { name: WORKSPACE_COPY.clarifyBack })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: thermal.title })).not.toBeInTheDocument();
  });

  it('blocks Next on an unanswered required question and shows why', async () => {
    const form = await openQuestions();
    click(form, WORKSPACE_COPY.clarifyNext);
    expect(within(form).getByText('Answer this question to continue.')).toBeInTheDocument();
    expect(within(form).getByText('Question 1 of 4')).toBeInTheDocument();
    expect(within(form).getByRole('radio', { name: 'Thermal overload' })).toHaveFocus();
  });

  it('steps forward and back, keeps answers and focuses each new question', async () => {
    const form = await openQuestions();
    fireEvent.click(within(form).getByRole('radio', { name: 'Thermal overload' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    expect(within(form).getByText('Question 2 of 4')).toBeInTheDocument();
    expect(within(form).getByRole('checkbox', { name: 'West' })).toHaveFocus();
    click(form, WORKSPACE_COPY.clarifyBack);
    expect(within(form).getByRole('radio', { name: 'Thermal overload' })).toBeChecked();
  });

  it('offers Skip on a blank optional question and keeps slider and field in step', async () => {
    const form = await openQuestions();
    fireEvent.click(within(form).getByRole('radio', { name: 'Thermal overload' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    fireEvent.click(within(form).getByRole('checkbox', { name: 'West' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    expect(within(form).getByRole('slider')).toHaveAttribute('aria-valuetext', WORKSPACE_COPY.clarifyNotSet);
    expect(within(form).getByRole('button', { name: WORKSPACE_COPY.clarifySkip })).toBeInTheDocument();
    fireEvent.change(within(form).getByRole('slider'), { target: { value: '45' } });
    expect(within(form).getByRole('spinbutton')).toHaveValue(45);
    expect(within(form).getByRole('button', { name: WORKSPACE_COPY.clarifyNext })).toBeInTheDocument();
    fireEvent.change(within(form).getByRole('spinbutton'), { target: { value: '90' } });
    expect(within(form).getByRole('slider')).toHaveAttribute('aria-valuetext', '90 min');
    click(form, WORKSPACE_COPY.clarifyClear);
    expect(within(form).getByRole('spinbutton')).toHaveValue(null);
  });

  it('sends every answer together after the last question and returns the scenario', async () => {
    const spy = vi.spyOn(api, 'solveSituation');
    const form = await openQuestions();
    fireEvent.click(within(form).getByRole('radio', { name: 'Low voltage' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    fireEvent.click(within(form).getByRole('checkbox', { name: 'North-west' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    click(form, WORKSPACE_COPY.clarifySkip);
    expect(within(form).getByText('Question 4 of 4')).toBeInTheDocument();
    expect(spy).toHaveBeenCalledTimes(1);
    click(form, WORKSPACE_COPY.clarifySubmit);
    await screen.findByRole('region', { name: illustrativeScenarios[1].title });
    expect(screen.queryByRole('region', { name: WORKSPACE_COPY.clarifyTitle })).not.toBeInTheDocument();
    expect(spy).toHaveBeenLastCalledWith(
      {
        description: 'there is a problem',
        threadId: null,
        caseSummary: expect.stringContaining('Reviewed facts:'),
        answers: [
          { round: 1, questionId: 'limit', value: 'low_voltage' },
          { round: 1, questionId: 'area', value: ['north_west'] },
          { round: 1, questionId: 'lead_time', value: null },
          { round: 1, questionId: 'detail', value: null },
        ],
      },
      expect.any(AbortSignal),
    );
  });

  it('starts again without an answer', async () => {
    const form = await openQuestions();
    click(form, WORKSPACE_COPY.clarifyCancel);
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });

  it('shows an error instead of rendering malformed questions', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(api, 'solveSituation').mockResolvedValue({
      kind: 'clarification',
      threadId: null,
      clarification: { reason: 'x', questions: [{ id: 'q', kind: 'date' }] } as never,
    });
    render(<AssistantApp />);
    await submitSituation('anything');
    expect(await screen.findByText(WORKSPACE_COPY.solverErrorTitle)).toBeInTheDocument();
    expect(screen.getByText(/cannot show/)).toBeInTheDocument();
  });

  it('stops after the maximum number of rounds', async () => {
    vi.spyOn(api, 'solveSituation').mockResolvedValue({
      kind: 'clarification',
      threadId: 'thread-1',
      clarification: {
        reason: 'Still need detail.',
        questions: [{ id: 'note', kind: 'text', prompt: 'More?', helpText: null, required: false, placeholder: null, maxLength: null }],
      },
    });
    render(<AssistantApp />);
    await submitSituation('anything');
    for (let round = 1; round <= MAX_CLARIFICATION_ROUNDS; round += 1) {
      const form = await screen.findByRole('region', { name: new RegExp(WORKSPACE_COPY.clarifyTitle) });
      fireEvent.click(within(form).getByRole('button', { name: WORKSPACE_COPY.clarifySubmit }));
    }
    const stopped = await screen.findByText(WORKSPACE_COPY.stoppedTitle);
    expect(stopped.parentElement).toHaveTextContent('More?');
    expect(screen.queryByText(WORKSPACE_COPY.solverErrorTitle)).not.toBeInTheDocument();
    expect(api.solveSituation).toHaveBeenLastCalledWith(
      expect.objectContaining({
        threadId: 'thread-1',
        // Every round reuses the ID "note"; each round's answer is kept.
        answers: [
          { round: 1, questionId: 'note', value: null },
          { round: 2, questionId: 'note', value: null },
          { round: 3, questionId: 'note', value: null },
        ],
      }),
      expect.any(AbortSignal),
    );
    fireEvent.click(screen.getByRole('button', { name: WORKSPACE_COPY.clarifyCancel }));
    expect(screen.queryByText(WORKSPACE_COPY.stoppedTitle)).not.toBeInTheDocument();
    expect(localStorage.length).toBe(0);
  });

  it('resumes the open questions after a reload', async () => {
    const spy = vi.spyOn(api, 'solveSituation');
    const { unmount } = render(<AssistantApp />);
    await submitSituation('there is a problem');
    await screen.findByRole('region', { name: WORKSPACE_COPY.clarifyTitle });
    unmount();
    render(<AssistantApp />);
    const form = screen.getByRole('region', { name: WORKSPACE_COPY.clarifyTitle });
    expect(within(form).getByText('Question 1 of 4')).toBeInTheDocument();
    expect(within(form).getByText('there is a problem')).toBeInTheDocument();
    // Restored from storage, not asked again.
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('keeps the answers in the saved case', async () => {
    const form = await openQuestions();
    fireEvent.click(within(form).getByRole('radio', { name: 'Low voltage' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    fireEvent.click(within(form).getByRole('checkbox', { name: 'North-west' }));
    click(form, WORKSPACE_COPY.clarifyNext);
    click(form, WORKSPACE_COPY.clarifySkip);
    click(form, WORKSPACE_COPY.clarifySubmit);
    await screen.findByRole('region', { name: illustrativeScenarios[1].title });
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) as string);
    expect(saved.operatorCase.originalText).toBe('there is a problem');
    expect(saved.operatorCase.facts.limit).toMatchObject({ value: 'low_voltage', status: 'operator_supplied', source: 'operator' });
    expect(saved.operatorCase.facts.area.value).toBe('north_west');
    expect(saved.operatorCase.facts.lead_time).toBeUndefined();
    expect(saved.state.status).toBe('solved');
  });
});

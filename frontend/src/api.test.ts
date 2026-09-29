import { afterEach, describe, expect, it, vi } from 'vitest';
import { splitReply } from './components/AssistantReplyCard';

// Live mode: tests otherwise always run against fixtures.
vi.mock('./mode', () => ({ USE_FIXTURE: false }));

const { askWorkspaceCase, chatMessage, solveSituation, SolverUnavailableError } = await import('./api');
const { DEFAULT_TARGET, fetchDispatchDown } = await import('./dispatchDown');

function request(description: string, threadId: string | null = null) {
  return { description, threadId, answers: [] };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

afterEach(() => vi.restoreAllMocks());

describe('reviewed case workspace route', () => {
  it('posts the reviewed case to the structured evaluator', async () => {
    const operatorCase = {
      id: 'case-1',
      originalText: 'Line overload in the west after the outage',
      createdAt: '2026-09-29T12:00:00Z',
      scenarios: ['local_network_constraint', 'planned_outage_exposure'],
      facts: {},
      proposedAction: null,
      comparison: null,
    };
    const scenario = {
      id: 'case-1',
      title: 'Thermal capacity advisory — T3',
      intervalStart: '2026-09-29T13:00:00Z',
      intervalEnd: '2026-09-30T13:00:00Z',
      source: 'live',
      modelRunAt: null,
      summary: 'Evidence-gated planning result.',
      keywords: [],
      binding: null,
      action: null,
      noActionReason: 'No action has complete evidence for recommendation.',
      baseline: { securityResult: 'unknown', dispatchDownWasteMwh: null },
      postAction: null,
      impact: null,
      guardrails: [],
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ kind: 'scenario', scenario }));
    const result = await solveSituation({
      description: operatorCase.originalText,
      threadId: null,
      answers: [],
      caseSummary: 'Reviewed facts',
      operatorCase,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/workspace/evaluate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ case: operatorCase }),
      }),
    );
    expect(result).toEqual({ kind: 'scenario', scenario });
  });

  it('sends a reviewed demo case to the Azure explanation endpoint', async () => {
    const operatorCase = { id: 'case-1', originalText: 'Planned outage near Ballylickey' };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ reply: 'This is a modeled candidate.', model: 'gpt-4.1' }));
    await expect(askWorkspaceCase(operatorCase, 'Why?')).resolves.toEqual({ reply: 'This is a modeled candidate.', model: 'gpt-4.1' });
    expect(fetchMock).toHaveBeenCalledWith('/v1/workspace/ask', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ case: operatorCase, question: 'Why?', history: [] }),
    }));
  });
});

describe('live solver through the LangGraph chat route', () => {
  it('posts the description to /v1/chat in its request shape', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({
      thread_id: 't1', reply: 'High risk.\nRecommended action: A2 - flexible demand', tools_used: ['get_dispatch_down_forecast'], model: 'gpt-4.1',
    }));
    const result = await solveSituation(request('What is the dispatch-down risk at 2026-01-24 01:00, and what should I do?'));
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe('/v1/chat');
    expect(JSON.parse(String(init?.body))).toEqual({
      message: 'What is the dispatch-down risk at 2026-01-24 01:00, and what should I do?',
      thread_id: null,
      selected_target: '2026-01-24T01:00',
    });
    expect(result).toEqual({
      kind: 'assistant_reply',
      reply: { threadId: 't1', text: 'High risk.\nRecommended action: A2 - flexible demand', toolsUsed: ['get_dispatch_down_forecast'], model: 'gpt-4.1', trace: [] },
      target: '2026-01-24T01:00',
    });
  });

  it('shows the forecast view for dispatch-down replies, at the default time when none is named', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ thread_id: 't1', reply: 'High risk.', tools_used: ['get_dispatch_down_day'], model: 'gpt-4.1' }));
    await expect(solveSituation(request('how does today look?'))).resolves.toMatchObject({ target: DEFAULT_TARGET });
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ thread_id: 't1', reply: 'High risk.', tools_used: [], model: 'gpt-4.1' }));
    await expect(solveSituation(request('what is the dispatch-down risk?'))).resolves.toMatchObject({ target: DEFAULT_TARGET });
  });

  it('shows no forecast view for replies that are not about dispatch-down', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ thread_id: 't1', reply: 'Hello.', tools_used: [], model: 'gpt-4.1' }));
    await expect(solveSituation(request('hello'))).resolves.toMatchObject({ kind: 'assistant_reply', target: null });
  });

  it('falls back to the real dispatch-down view when chat is not configured', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Azure OpenAI is not configured.' }, 503));
    await expect(solveSituation(request('dispatch-down risk at 2026-01-20 14:30')))
      .resolves.toEqual({ kind: 'dispatch_down_risk', target: '2026-01-20T14:30' });
    await expect(solveSituation(request('DD next hour')))
      .resolves.toEqual({ kind: 'dispatch_down_risk', target: DEFAULT_TARGET });
  });

  it('reports the assistant as unavailable for other questions when chat is not configured', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Azure OpenAI is not configured.' }, 503));
    const error = await solveSituation(request('line overload in the west')).catch((err) => err);
    expect(error).toBeInstanceOf(SolverUnavailableError);
    expect(error.message).toBe('Azure OpenAI is not configured.');
  });

  it('surfaces rate limits as an error the operator can retry', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Azure OpenAI is busy (shared rate limit). Try again shortly.' }, 429));
    await expect(solveSituation(request('line overload in the west'))).rejects.toThrow(/busy/);
  });

  it('sends follow-up answers as one message on the same thread', () => {
    expect(chatMessage({
      description: 'there is a problem',
      threadId: 't1',
      answers: [
        { round: 1, questionId: 'area', value: ['west', 'dublin'] },
        { round: 1, questionId: 'detail', value: null },
      ],
    })).toBe('Answers to your follow-up questions about: there is a problem\n- round 1, area: west, dublin\n- round 1, detail: (left blank)');
  });

  it('calls the real dispatch-down API, not the fixture', async () => {
    const body = { mode: 'historical_replay', risk: 'low' };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(body));
    await expect(fetchDispatchDown('2026-01-20T14:30')).resolves.toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/dispatch-down/forecast?target_timestamp=2026-01-20T14%3A30%3A00Z',
      expect.anything(),
    );
  });
});

describe('splitReply', () => {
  it('pulls out the select_action recommendation line', () => {
    expect(splitReply('High risk: 95.4%.\n\n**Recommended action:** A2 - Dispatch change\nBecause demand can absorb it.')).toEqual({
      body: ['High risk: 95.4%.', 'Because demand can absorb it.'],
      recommendation: 'A2 - Dispatch change',
    });
    expect(splitReply('Just an answer.')).toEqual({ body: ['Just an answer.'], recommendation: null });
  });
});

describe('run trace', () => {
  it('passes the graph path through and counts loop edges', async () => {
    const trace = [
      { node: '__start__', detail: '' },
      { node: 'load_actions', detail: 'loaded 6 candidate actions' },
      { node: 'agent', detail: 'requested get_dispatch_down_forecast' },
      { node: 'tools', detail: 'ran get_dispatch_down_forecast' },
      { node: 'agent', detail: 'requested get_dispatch_down_day' },
      { node: 'tools', detail: 'ran get_dispatch_down_day' },
      { node: 'agent', detail: 'drafted an answer' },
      { node: 'select_action', detail: 'A2 - Dispatch change' },
      { node: '__end__', detail: '' },
    ];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ thread_id: 't1', reply: 'x', tools_used: [], model: 'm', trace }));
    const result = await solveSituation(request('hello'));
    expect(result).toMatchObject({ reply: { trace } });
    const { edgeCounts } = await import('./components/RunTraceDiagram');
    const counts = edgeCounts(trace);
    expect(counts.get('agent->tools')).toBe(2);
    expect(counts.get('tools->agent')).toBe(2);
    expect(counts.get('agent->select_action')).toBe(1);
  });

  it('defaults to an empty trace from an older API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ thread_id: 't1', reply: 'x', tools_used: [], model: 'm' }));
    await expect(solveSituation(request('hello'))).resolves.toMatchObject({ reply: { trace: [] } });
  });
});

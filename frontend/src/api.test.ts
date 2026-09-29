import { describe, expect, it, vi } from 'vitest';

// Live mode: tests otherwise always run against fixtures.
vi.mock('./mode', () => ({ USE_FIXTURE: false }));

const { solveSituation, SolverUnavailableError } = await import('./api');
const { DEFAULT_TARGET, fetchDispatchDown } = await import('./dispatchDown');

function request(description: string) {
  return { description, threadId: null, answers: [] };
}

describe('live solver without the LLM', () => {
  it('sends dispatch-down questions to the dispatch-down view', async () => {
    await expect(solveSituation(request('dispatch-down risk at 2026-01-20 14:30')))
      .resolves.toEqual({ kind: 'dispatch_down_risk', target: '2026-01-20T14:30' });
    await expect(solveSituation(request('DD next hour')))
      .resolves.toEqual({ kind: 'dispatch_down_risk', target: DEFAULT_TARGET });
  });

  it('still reports the scenario solver as not connected for other questions', async () => {
    await expect(solveSituation(request('line overload in the west'))).rejects.toBeInstanceOf(SolverUnavailableError);
  });

  it('calls the real dispatch-down API, not the fixture', async () => {
    const body = { mode: 'historical_replay', risk: 'low' };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(body)));
    await expect(fetchDispatchDown('2026-01-20T14:30')).resolves.toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/dispatch-down/forecast?target_timestamp=2026-01-20T14%3A30%3A00Z',
      expect.anything(),
    );
    fetchMock.mockRestore();
  });
});

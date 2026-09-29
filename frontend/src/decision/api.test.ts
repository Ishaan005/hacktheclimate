import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.resetModules();
});

// Live mode is selected by the build mode, so load the module with it off.
async function liveApi() {
  vi.doMock('../mode', () => ({ USE_FIXTURE: false }));
  return import('./api');
}

const request = { description: 'x', view: 'national' as const, siteId: null, conditions: [], facts: [], edits: [], alternative: null };

describe('assessDecision in live mode', () => {
  it('reports unavailable, not an error, while the backend route does not exist', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 405 })));
    const { assessDecision } = await liveApi();
    const result = await assessDecision(request);
    expect(result.status).toBe('unavailable');
    if (result.status === 'unavailable') expect(result.reason).toContain('HTTP 405');
  });

  it('reports unavailable when the API cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const { assessDecision } = await liveApi();
    expect((await assessDecision(request)).status).toBe('unavailable');
  });
});

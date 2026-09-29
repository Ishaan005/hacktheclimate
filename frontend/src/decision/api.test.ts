import { afterEach, describe, expect, it, vi } from 'vitest';
import { fixtureAssessment } from './fixture';
import { DEMO_SITES } from './sites';

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

async function fixtureApi() {
  vi.doMock('../mode', () => ({ USE_FIXTURE: true }));
  return import('./api');
}

const request = { description: 'x', view: 'national' as const, siteId: null, conditions: [], facts: [], edits: [], alternative: null };

describe('assessDecision in live mode', () => {
  it('reports unavailable when the assessment API responds unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 405 })));
    const { assessDecision } = await liveApi();
    const result = await assessDecision(request);
    expect(result.status).toBe('unavailable');
    if (result.status === 'unavailable') expect(result.reason).toContain('HTTP 405');
    expect(fetch).toHaveBeenCalledWith('/v1/workspace/assess', expect.objectContaining({ method: 'POST' }));
  });

  it('reports unavailable when the API cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const { assessDecision } = await liveApi();
    expect((await assessDecision(request)).status).toBe('unavailable');
  });
});

describe('assessDecision in fixture mode', () => {
  it('returns plant-specific safety and plans while preserving all-island checks', async () => {
    const { assessDecision } = await fixtureApi();
    const assessments = await Promise.all(DEMO_SITES.map(async (site) => {
      const response = await assessDecision({ ...request, description: 'route overload during outage',
        view: 'precise', siteId: site.id, conditions: fixtureAssessment.conditions });
      if (response.status !== 'ok') throw new Error(`No demo assessment for ${site.id}`);
      return response.assessment;
    }));
    expect(assessments.map((assessment) => assessment.familyChecks.find((check) => check.id === 'fc-flow')?.value))
      .toEqual(['406 MW', '419 MW', '426 MW']);
    expect(assessments.map((assessment) => assessment.proposed?.steps[0].instruction))
      .toEqual([
        'Reduce Ballybane 2 by 40 MW; increase Tynagh CCGT by 40 MW.',
        'Reduce Ballybane 3 by 35 MW; increase Tynagh CCGT by 35 MW.',
        'Charge Battery C at 15 MW.',
      ]);
    expect(assessments.map((assessment) => assessment.outcomes.find((outcome) => outcome.column === 'proposed')?.deliveredReliefMw.value))
      .toEqual([44, 31, 24]);
    expect(assessments.map((assessment) => assessment.allIslandChecks[0].value))
      .toEqual(['72.4%', '72.4%', '72.4%']);
    expect(assessments.every((assessment) => assessment.overall.result === 'unknown' && !assessment.validated))
      .toBe(true);
  });
});

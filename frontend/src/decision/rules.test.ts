import { describe, expect, it } from 'vitest';
import { fixtureAssessment } from './fixture';
import { canClaimBenefit, combineResults, displayOverall, planLabel, windowMismatches } from './rules';
import { hintsFor, matchDescription, SUGGESTIONS } from './scope';
import type { Assessment, Plan, SafetyCheck } from './types';

function passing(check: SafetyCheck): SafetyCheck {
  return { ...check, result: 'pass' };
}

// A validated assessment where every check passes and every fact is current.
function cleanAssessment(): Assessment {
  return {
    ...fixtureAssessment,
    validated: true,
    overall: { result: 'pass', reason: 'All checks pass.', missingEvidence: [] },
    facts: fixtureAssessment.facts.map((fact) => ({ ...fact, state: 'current' })),
    familyChecks: fixtureAssessment.familyChecks.map(passing),
    crossChecks: fixtureAssessment.crossChecks.map(passing),
    allIslandChecks: fixtureAssessment.allIslandChecks.map(passing),
    actionChecks: fixtureAssessment.actionChecks.map((check) => ({ ...check, result: 'pass' })),
  };
}

function cleanPlan(permissionState: 'pending' | 'confirmed'): Plan {
  const plan = fixtureAssessment.proposed!;
  return {
    ...plan,
    label: 'actionable',
    steps: plan.steps.map((step) => ({ ...step, blockingCheckIds: [], permissionState: step.permissionRoute === 'direct' ? 'confirmed' : permissionState })),
  };
}

describe('combineResults', () => {
  it('treats no checks as unknown, not pass', () => {
    expect(combineResults([])).toBe('unknown');
    expect(combineResults(['pass', 'unknown'])).toBe('unknown');
    expect(combineResults(['unknown', 'fail'])).toBe('fail');
    expect(combineResults(['pass', 'pass'])).toBe('pass');
  });
});

describe('displayOverall', () => {
  it('keeps a pass unknown while a fact is stale, missing or conflicting', () => {
    const assessment = cleanAssessment();
    const withStale = { ...assessment, facts: [{ ...assessment.facts[0], state: 'stale' as const }] };
    const overall = displayOverall(withStale, false);
    expect(overall.result).toBe('unknown');
    expect(overall.missingEvidence[0]).toContain('stale');
  });

  it('never passes an unvalidated or out-of-date assessment', () => {
    expect(displayOverall({ ...cleanAssessment(), validated: false }, false).result).toBe('unknown');
    expect(displayOverall(cleanAssessment(), true).result).toBe('unknown');
    expect(displayOverall(cleanAssessment(), false).result).toBe('pass');
  });
});

describe('planLabel', () => {
  it('marks a proposal unsafe when a family check fails', () => {
    const failing = { ...fixtureAssessment, familyChecks: [{ ...fixtureAssessment.familyChecks[0], result: 'fail' as const }] };
    expect(planLabel(fixtureAssessment.proposed!, failing, false).label).toBe('unsafe');
    expect(planLabel(fixtureAssessment.proposed!, fixtureAssessment, false).label).toBe('insufficient_evidence');
  });

  it('reports insufficient evidence when a required check is unknown', () => {
    const assessment = cleanAssessment();
    assessment.familyChecks = [{ ...assessment.familyChecks[0], result: 'unknown' }];
    expect(planLabel(cleanPlan('confirmed'), assessment, false).label).toBe('insufficient_evidence');
  });

  it('stays conditional until the other party accepts', () => {
    const assessment = cleanAssessment();
    expect(planLabel(cleanPlan('pending'), assessment, false).label).toBe('conditional');
    expect(planLabel(cleanPlan('confirmed'), assessment, false).label).toBe('actionable');
  });

  it('is never actionable once the assessment is stale', () => {
    expect(planLabel(cleanPlan('confirmed'), cleanAssessment(), true).label).toBe('insufficient_evidence');
  });

  it('shows the more cautious of the backend and derived labels', () => {
    const plan = { ...cleanPlan('confirmed'), label: 'conditional' as const, labelReason: 'Backend waits for WDT confirmation.' };
    expect(planLabel(plan, cleanAssessment(), false)).toEqual({ label: 'conditional', reason: 'Backend waits for WDT confirmation.' });
  });

  it('ignores action checks for steps outside the plan', () => {
    const assessment = cleanAssessment();
    assessment.actionChecks = [...assessment.actionChecks, { ...assessment.actionChecks[0], id: 'other', stepId: 'not-in-plan', result: 'fail' }];
    expect(planLabel(cleanPlan('confirmed'), assessment, false).label).toBe('actionable');
  });
});

describe('comparison rules', () => {
  it('lets only a safe, evaluated plan claim a benefit', () => {
    const proposed = fixtureAssessment.outcomes.find((outcome) => outcome.column === 'proposed');
    expect(canClaimBenefit(proposed)).toBe(false);
    expect(canClaimBenefit(proposed && { ...proposed, safety: 'pass' })).toBe(true);
  });

  it('flags a column with another window or without the active instructions', () => {
    expect(windowMismatches(fixtureAssessment.outcomes)).toEqual([]);
    const shifted = fixtureAssessment.outcomes.map((outcome) => (outcome.column === 'proposed' ? { ...outcome, windowEnd: '2026-01-24T19:00:00Z' } : outcome));
    expect(windowMismatches(shifted)).toEqual(['proposed']);
  });
});

describe('locked scope', () => {
  it('suggests only the nine locked scenarios', () => {
    expect(new Set(SUGGESTIONS.map((item) => item.scenarioId))).toEqual(new Set(['T1', 'T2', 'T3', 'T4', 'H1', 'H2', 'H3', 'H4', 'SNSP']));
  });

  it('keeps a forecast surplus in intake', () => {
    expect(matchDescription('forecast surplus overnight, frequency normal').kind).toBe('cause_unknown');
  });

  it('matches several limits at once', () => {
    const result = matchDescription('line overloaded during an outage and SNSP near the limit');
    expect(result.kind).toBe('matched');
    if (result.kind === 'matched') expect(result.suggestions.map((item) => item.scenarioId)).toEqual(expect.arrayContaining(['T3', 'SNSP']));
  });

  it('reports cause unknown for text outside the scope', () => {
    expect(matchDescription('low voltage in the north-west').kind).toBe('cause_unknown');
  });
});

describe('transmission matching', () => {
  it('resolves one sentence to exactly one of the four conditions', () => {
    const ids = (text: string) => {
      const result = matchDescription(text);
      return result.kind === 'matched' ? result.suggestions.map((item) => item.scenarioId) : [];
    };
    expect(ids('route overloaded during an outage')).toEqual(['T3']);
    expect(ids('safe during the outage but one further trip would overload it')).toEqual(['T4']);
    expect(ids('safe now but one trip would overload the line')).toEqual(['T2']);
    expect(ids('line overloaded with all equipment in service')).toEqual(['T1']);
  });
});

describe('overall display', () => {
  it('shows fail when a required check fails, whatever the backend overall says', () => {
    const assessment = { ...fixtureAssessment, familyChecks: [{ ...fixtureAssessment.familyChecks[0], result: 'fail' as const }] };
    expect(displayOverall(assessment, false).result).toBe('fail');
  });
});

describe('hintsFor', () => {
  it('turns free text into locked scenario hints with no typed details', () => {
    const { conditions, causeUnknown } = hintsFor('route overloaded during an outage and SNSP near the limit');
    expect(causeUnknown).toBeNull();
    expect(conditions.map((item) => item.scenarioId)).toEqual(['T3', 'SNSP']);
    expect(conditions.every((item) => item.limitingAsset === null && item.timeSetting === null)).toBe(true);
  });

  it('returns cause unknown with the facts needed when nothing in scope matches', () => {
    const { conditions, causeUnknown } = hintsFor('something odd is happening');
    expect(conditions).toEqual([]);
    expect(causeUnknown?.factsNeeded.length).toBeGreaterThan(0);
  });
});

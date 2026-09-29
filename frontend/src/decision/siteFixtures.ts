// Offline planning variants for the named plants. These are invented demo
// cases, not studied plant connections, safe dispatch instructions or forecasts.
import { fixtureAssessment } from './fixture';
import { DEMO_SITES } from './sites';
import type { Assessment, PlanStep } from './types';

type SiteVariant = {
  flowMw: number;
  responseMinutes: number;
  reliefMw: number;
  proposedMwh: number;
  planName: string;
  steps: PlanStep[];
  actionChecks: Assessment['actionChecks'];
  crossChecks: Assessment['crossChecks'];
};

const [ballybane2, ballybane3, curraglass] = DEMO_SITES;
const basePlan = fixtureAssessment.proposed!;
const [baseRedispatch, baseBattery] = basePlan.steps;

const variants: Record<string, SiteVariant> = {
  [ballybane2.id]: {
    flowMw: 406,
    responseMinutes: 20,
    reliefMw: 44,
    proposedMwh: 20,
    planName: 'Ballybane 2 redispatch with battery charging',
    steps: [
      { ...baseRedispatch,
        instruction: 'Reduce Ballybane 2 by 40 MW; increase Tynagh CCGT by 40 MW.',
        executor: `${ballybane2.name} / Tynagh CCGT` },
      baseBattery,
    ],
    actionChecks: fixtureAssessment.actionChecks,
    crossChecks: fixtureAssessment.crossChecks,
  },
  [ballybane3.id]: {
    flowMw: 419,
    responseMinutes: 25,
    reliefMw: 31,
    proposedMwh: 25,
    planName: 'Ballybane 3 generator redispatch',
    steps: [
      { ...baseRedispatch,
        instruction: 'Reduce Ballybane 3 by 35 MW; increase Tynagh CCGT by 35 MW.',
        executor: `${ballybane3.name} / Tynagh CCGT`,
        effectTime: '2026-01-24T16:25:00Z', mwEffect: -31 },
    ],
    actionChecks: fixtureAssessment.actionChecks.filter((check) => check.stepId === 'step-1').map((check) => (
      check.id === 'ac-redispatch-match'
        ? { ...check, value: '−35 / +35 MW' }
        : { ...check, value: '3 MW/min', limit: '1.4 MW/min needed', margin: '1.6 MW/min' }
    )),
    crossChecks: [],
  },
  [curraglass.id]: {
    flowMw: 426,
    responseMinutes: 12,
    reliefMw: 24,
    proposedMwh: 27,
    planName: 'Curraglass local charging and flexible demand',
    steps: [
      { ...baseBattery, id: 'step-1', role: 'main',
        instruction: 'Charge Battery C at 15 MW.', executor: 'Battery C',
        startTime: '2026-01-24T16:00:00Z', effectTime: '2026-01-24T16:05:00Z',
        mwEffect: -15, dependsOn: [] },
      { ...baseBattery, id: 'step-2', role: 'supporting',
        instruction: 'Increase flexible demand at Curraglass by 9 MW.',
        executor: 'Curraglass flexible demand',
        permissionRoute: 'needs_acceptance', permissionState: 'pending',
        permissionParty: 'Flexible demand operator',
        startTime: '2026-01-24T16:00:00Z', effectTime: '2026-01-24T16:12:00Z',
        mwEffect: -9, dependsOn: [], blockingCheckIds: ['ac-demand-location'] },
    ],
    actionChecks: [
      { ...fixtureAssessment.actionChecks[2], stepId: 'step-1', value: '15 MW',
        reason: 'No meter confirms Battery C is behind the limiting route.' },
      { ...fixtureAssessment.actionChecks[3], stepId: 'step-1' },
      { ...fixtureAssessment.actionChecks[2], id: 'ac-demand-location', stepId: 'step-2',
        label: 'Metered flexible demand behind the bottleneck', value: '9 MW',
        reason: 'The flexible demand location and availability are not confirmed.' },
    ],
    crossChecks: [{ ...fixtureAssessment.crossChecks[0], value: null, margin: null,
      result: 'unknown', reason: 'Battery C frequency-service headroom is not confirmed.' }],
  },
};

export function fixtureAssessmentForSite(siteId: string): Assessment | null {
  const variant = variants[siteId];
  if (!variant) return null;
  const base = fixtureAssessment;
  const marginMw = 431 - variant.flowMw;
  const leadMinutes = 35 - variant.responseMinutes;
  const proposedMwh = variant.proposedMwh;
  return {
    ...base,
    familyChecks: base.familyChecks.map((check) => {
      if (check.id === 'fc-flow') return { ...check,
        value: `${variant.flowMw} MW`, margin: `+${marginMw} MW`,
        source: 'Illustrative site planning case',
        reason: 'Illustrative route flow only; the plant connection and contingency study are not verified.' };
      if (check.id === 'fc-relief') return { ...check,
        value: `${variant.responseMinutes} min`, margin: `${leadMinutes} min`,
        source: 'Illustrative site timing' };
      return check;
    }),
    crossChecks: variant.crossChecks,
    actionChecks: variant.actionChecks,
    proposed: { ...basePlan, name: variant.planName, steps: variant.steps },
    outcomes: base.outcomes.map((outcome) => outcome.column === 'proposed'
      ? { ...outcome,
        worstMargin: `+${marginMw} MW`,
        deliveredReliefMw: { ...outcome.deliveredReliefMw, value: variant.reliefMw, lower: null, upper: null },
        responseTimeMinutes: { ...outcome.responseTimeMinutes, value: variant.responseMinutes, lower: null, upper: null },
        constrainedMwh: { ...outcome.constrainedMwh, value: proposedMwh, lower: null, upper: null },
      }
      : outcome),
    benefits: { ...base.benefits,
      avoidedDispatchDownMwh: { ...base.benefits.avoidedDispatchDownMwh,
        value: 40 - proposedMwh, lower: null, upper: null } },
    evidence: { ...base.evidence,
      actionDecisions: variant.steps.map((step) => ({ stepId: step.id, kind: step.kind,
        decision: 'conditional' as const,
        reason: 'Illustrative action; plant connection and safety studies are unverified.' })),
      assumptions: ['Plant response and route effects are illustrative; the connection is not verified.'],
      auditId: `demo-${siteId}` },
  };
}

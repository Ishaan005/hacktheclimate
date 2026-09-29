// Display rules for the decision workspace. These never create a safety
// result: they only make sure the screen is at least as cautious as the
// backend assessment it shows.

import type { ActionSafetyCheck, Assessment, ComparisonColumn, OutcomeState, OverallSafety, Plan, PlanLabel, SafetyCheck, SafetyResult, SituationFact } from './types';

// Most cautious first.
const LABEL_ORDER: PlanLabel[] = ['unsafe', 'insufficient_evidence', 'conditional', 'actionable'];

export function moreCautious(a: PlanLabel, b: PlanLabel): PlanLabel {
  return LABEL_ORDER.indexOf(a) <= LABEL_ORDER.indexOf(b) ? a : b;
}

// Fail wins over unknown; unknown wins over pass. An empty list is unknown:
// no checks is not evidence of safety.
export function combineResults(results: SafetyResult[]): SafetyResult {
  if (!results.length) return 'unknown';
  if (results.includes('fail')) return 'fail';
  if (results.includes('unknown')) return 'unknown';
  return 'pass';
}

// Action-specific checks for the steps in this plan only.
export function checksForPlan(plan: Plan, actionChecks: ActionSafetyCheck[]): ActionSafetyCheck[] {
  const stepIds = new Set(plan.steps.map((step) => step.id));
  return actionChecks.filter((check) => stepIds.has(check.stepId));
}

// Missing, stale or conflicting facts keep the result Unknown, whatever the
// backend said. A fail stays a fail.
export function uncertainFacts(facts: SituationFact[]): SituationFact[] {
  return facts.filter((fact) => fact.state !== 'current');
}

export function displayOverall(
  assessment: Pick<Assessment, 'overall' | 'facts' | 'validated'> & Partial<Pick<Assessment, 'familyChecks' | 'crossChecks' | 'allIslandChecks'>>,
  stale: boolean,
): OverallSafety {
  const { overall } = assessment;
  if (overall.result === 'fail') return overall;
  // A failed required check is never shown under a milder overall result.
  const failed = [...(assessment.familyChecks ?? []), ...(assessment.crossChecks ?? []), ...(assessment.allIslandChecks ?? [])]
    .filter((check) => check.result === 'fail');
  if (failed.length) {
    return { result: 'fail', reason: `A required check fails: ${failed.map((check) => check.label).join(', ')}.`, missingEvidence: overall.missingEvidence };
  }
  const uncertain = uncertainFacts(assessment.facts);
  if (overall.result === 'pass' && stale) {
    return { result: 'unknown', reason: 'Inputs or plan changed after the last assessment. Rerun it.', missingEvidence: [] };
  }
  if (overall.result === 'pass' && uncertain.length) {
    return {
      result: 'unknown',
      reason: 'Some facts are missing, stale or conflicting.',
      missingEvidence: uncertain.map((fact) => `${fact.label} (${fact.state})`),
    };
  }
  if (overall.result === 'pass' && !assessment.validated) {
    return { result: 'unknown', reason: 'Pass needs an operational assessment with every required check connected.', missingEvidence: [] };
  }
  return overall;
}

export type DerivedLabel = { label: PlanLabel; reason: string };

// Unsafe: a required check fails. Insufficient evidence: a required check is
// unknown, or the assessment is out of date. Conditional: a named agreement
// or clearance is not yet recorded. Actionable only when none of these holds.
// Family checks always apply; action checks add to them, never replace them.
export function planLabel(
  plan: Plan,
  assessment: Pick<Assessment, 'overall' | 'facts' | 'validated' | 'familyChecks' | 'crossChecks' | 'actionChecks' | 'allIslandChecks'>,
  stale: boolean,
): DerivedLabel {
  const overall = displayOverall(assessment, stale);
  const required: SafetyCheck[] = [
    ...assessment.familyChecks,
    ...assessment.crossChecks,
    ...assessment.allIslandChecks,
    ...checksForPlan(plan, assessment.actionChecks),
  ];
  const results = [overall.result, ...required.map((check) => check.result)];
  let derived: DerivedLabel;
  if (results.includes('fail')) {
    const failed = required.filter((check) => check.result === 'fail').map((check) => check.label);
    derived = { label: 'unsafe', reason: failed.length ? `Fails: ${failed.join(', ')}.` : overall.reason };
  } else if (stale) {
    derived = { label: 'insufficient_evidence', reason: 'The plan or its inputs changed after the last assessment. Rerun the assessment.' };
  } else if (results.includes('unknown') || !plan.steps.length) {
    const unknown = required.filter((check) => check.result === 'unknown').map((check) => check.label);
    derived = {
      label: 'insufficient_evidence',
      reason: unknown.length ? 'Required safety evidence is incomplete. See the evidence below.' : overall.reason,
    };
  } else {
    const pending = plan.steps.filter((step) => step.permissionRoute !== 'direct' && step.permissionState !== 'confirmed');
    const refused = plan.steps.filter((step) => step.permissionState === 'refused');
    if (refused.length) {
      derived = { label: 'unsafe', reason: `Refused by ${refused.map((step) => step.permissionParty ?? step.executor).join(', ')}.` };
    } else if (pending.length) {
      derived = {
        label: 'conditional',
        reason: `Waiting for ${pending.map((step) => step.permissionParty ?? step.executor).join(', ')} to ${pending.some((step) => step.permissionRoute === 'needs_acceptance') ? 'accept' : 'clear'}.`,
      };
    } else if (plan.steps.some((step) => step.blockingCheckIds.length > 0)) {
      derived = { label: 'insufficient_evidence', reason: 'A step still has a blocking check.' };
    } else {
      derived = { label: 'actionable', reason: 'All required safety, availability, timing and permission checks pass.' };
    }
  }
  // Show the more cautious of the backend label and the derived one.
  const label = moreCautious(derived.label, plan.label);
  return label === derived.label ? derived : { label, reason: plan.labelReason };
}

// A plan with a failed or unknown required safety check cannot win on
// benefits.
export function canClaimBenefit(outcome: OutcomeState | undefined): boolean {
  return outcome?.available === true && outcome.safety === 'pass';
}

export function outcomeFor(outcomes: OutcomeState[], column: ComparisonColumn): OutcomeState | undefined {
  return outcomes.find((outcome) => outcome.column === column);
}

// All four columns must share one window. Returns the mismatched columns.
export function windowMismatches(outcomes: OutcomeState[]): ComparisonColumn[] {
  const available = outcomes.filter((outcome) => outcome.available);
  const reference = available[0];
  if (!reference) return [];
  return available
    .filter((outcome) => outcome.windowStart !== reference.windowStart || outcome.windowEnd !== reference.windowEnd || !outcome.includesActiveInstructions)
    .map((outcome) => outcome.column);
}

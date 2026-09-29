// Words for the plan panel (UI brief section 5). Plain operator language.
// MW is a power change at the limiting location; never call it energy saved.

import type { PermissionRoute, PermissionState, PlanStep, SafetyResult } from '../types';

export const PLAN_COPY = {
  title: 'Proposed action plan',
  noSendNote: 'This app does not send instructions.',
  proposedHeading: 'Proposed plan',
  alternativeHeading: 'Operator alternative',
  noPlan: 'No proposed plan',
  // Short on purpose: the safety panel already gives the full reason.
  noPlanReason: {
    pass: 'The assessment found no action to propose.',
    fail: 'A safety check fails. See Safety.',
    unknown: 'Safety checks are incomplete. See Safety.',
  } satisfies Record<SafetyResult, string>,
  buildAlternative: 'Build an operator alternative',
  buildAlternativeHint: 'Choose the first action. You can add more steps after.',
  createAlternative: 'Create alternative',
  addStepLabel: 'Add a step',
  addStep: 'Add step',
  noSteps: 'This plan has no steps.',
  labelTitle: 'Plan label',
  editAsAlternative: 'Edit as alternative',
  editNote: 'Your changes go into a separate alternative. The proposal stays unchanged for comparison.',
  discardAlternative: 'Discard alternative',
  removeStep: 'Remove step',
  alternativeNote: 'Edits make the assessment out of date. Rerun it to check the whole combination again.',
  stepTitle: 'Step',
  notAvailable: 'Not available',
  none: 'None',
  unknownCheck: 'Unlisted check',
  removedStep: 'a step no longer in this plan',
  fields: {
    executor: 'Who',
    permission: 'Permission',
    startTime: 'Starts',
    effectTime: 'Effect arrives',
    duration: 'Lasts',
    mwEffect: 'MW at limiting location',
    blocking: 'Still blocked by',
    dependsOn: 'Starts after',
  },
  edit: {
    instruction: 'Instruction',
    executor: 'Asset or party',
    startTime: 'Start time (UTC)',
    mwEffect: 'MW change at limiting location',
    duration: 'Duration (min)',
    permissionState: 'Permission state',
  },
  mwHint: 'Negative relieves the limiting flow.',
  permissionPending: (party: string, state: PermissionState) => `Permission from ${party} (${PERMISSION_STATE_LABEL[state].toLowerCase()})`,
};

export const ROLE_LABEL: Record<PlanStep['role'], string> = {
  main: 'Main action',
  supporting: 'Supporting step',
  parallel: 'Parallel step',
};

export const PERMISSION_ROUTE_LABEL: Record<PermissionRoute, string> = {
  direct: 'Direct instruction',
  needs_clearance: 'Needs clearance',
  needs_acceptance: 'Needs acceptance',
};

export const PERMISSION_STATE_LABEL: Record<PermissionState, string> = {
  confirmed: 'Confirmed',
  pending: 'Pending',
  refused: 'Refused',
  unknown: 'Unknown',
};

// 'Direct instruction', or 'Needs acceptance by Tynagh generator owner'.
export function permissionText(route: PermissionRoute, party: string | null): string {
  if (route === 'direct') return PERMISSION_ROUTE_LABEL.direct;
  return `${PERMISSION_ROUTE_LABEL[route]} by ${party ?? 'an unnamed party'}`;
}

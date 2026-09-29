// Words for the evidence drawer (UI brief section 7). Plain operator
// language; the drawer never has to be read before the safety result.

import type { ActionDecision } from '../types';

export const DECISION_LABEL: Record<ActionDecision['decision'], string> = {
  included: 'Included',
  rejected: 'Rejected',
  conditional: 'Conditional',
};

export const EVIDENCE_COPY = {
  summary: 'Show the evidence',
  summaryHint: 'Sources, versions, limits and reasons behind this result',
  sourceTitle: 'Data source',
  validated: 'Validated assessment.',
  notValidated: 'Not a validated assessment. Do not rely on it for a live decision.',
  inputsTitle: 'Inputs used',
  inputColumns: { label: 'Input', source: 'Source', time: 'Time (UTC)', edited: 'Operator edit' },
  editedFlag: 'Edited by operator',
  notEdited: 'No',
  noInputs: 'No inputs listed.',
  editsTitle: 'Operator edits',
  noEdits: 'No operator edits.',
  edit: (fact: string, from: string, to: string) => `${fact}: ${from} changed to ${to}`,
  emptyValue: 'blank',
  versionsTitle: 'Rules and models',
  ruleVersion: 'Rule version',
  modelVersions: 'Model versions',
  limitsUsed: 'Limits used',
  credibleFailuresUsed: 'Credible failures used',
  actionsTitle: 'Why each action was included, rejected or left conditional',
  noActions: 'No action decisions recorded.',
  notInPlan: 'Not in plan',
  assumptionsTitle: 'Assumptions',
  uncertaintyTitle: 'Uncertainty',
  missingChecksTitle: 'Missing checks',
  assessedAt: 'Assessed at',
  auditId: 'Audit ID',
  feedsTitle: 'Feed freshness',
  noFeeds: 'No feeds listed.',
  asOf: 'as of',
  notRecorded: 'Not recorded',
  none: 'None listed',
};

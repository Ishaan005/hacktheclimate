// Situation table copy (UI brief section 3). Plain operator language.

import type { ScenarioFamily } from '../types';

export const SITUATION_COPY = {
  title: 'Situation',
  intro: 'Values available for this assessment, with their source and status. Edit an out-of-date or incorrect value before rerunning.',
  fact: 'Fact',
  value: 'Value',
  sourceTime: 'Source and time',
  origin: 'Origin',
  state: 'State',
  missing: 'Missing',
  noSource: 'No source recorded',
  noFacts: 'No facts recorded for these conditions.',
  edit: 'Edit',
  add: 'Add',
  save: 'Save',
  cancel: 'Cancel',
  editedWas: (previous: string) => `Edited (was ${previous})`,
  instructionsTitle: 'Current plan and instructions in force',
  noInstructions: 'No active instructions supplied; the instruction log is not connected.',
  instruction: 'Instruction',
  asset: 'Asset',
  issued: 'Issued',
  effectiveUntil: 'Effective until',
  source: 'Source',
  untilFurtherNotice: 'Until further notice',
  editsTitle: 'Operator edits',
  rerun: 'Rerun assessment',
} as const;

// Group headings in display order; general rows apply to every condition.
export const FACT_GROUP_LABEL: Record<ScenarioFamily | 'general', string> = {
  general: 'General',
  transmission: 'Transmission',
  high_frequency_minimum_generation: 'High frequency / minimum generation',
  snsp: 'SNSP',
};

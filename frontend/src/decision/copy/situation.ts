// Situation table copy (UI brief section 3). Plain operator language.

import type { DataStatus, ScenarioFamily } from '../types';

export const SITUATION_COPY = {
  title: 'Situation facts',
  intro: 'Values from connected feeds. Edit or add a value if it is missing, out of date or wrong.',
  fact: 'Fact',
  value: 'Value',
  sourceTime: 'Source and time',
  origin: 'Origin',
  state: 'State',
  missing: 'Missing',
  noSource: 'No source recorded',
  noFacts: 'No facts recorded for these conditions.',
  noSupplied: 'No facts supplied by connected feeds yet.',
  showMissing: (count: number) => `Show ${count} missing ${count === 1 ? 'fact' : 'facts'}`,
  hideMissing: (count: number) => `Hide ${count} missing ${count === 1 ? 'fact' : 'facts'}`,
  edit: 'Edit',
  add: 'Add',
  save: 'Save',
  cancel: 'Cancel',
  editedWas: (previous: string) => `Edited (was ${previous})`,
  instructionsTitle: 'Current plan and instructions in force',
  noInstructions: 'No current plan or instructions in force recorded.',
  instruction: 'Instruction',
  asset: 'Asset',
  issued: 'Issued',
  effectiveUntil: 'Effective until',
  source: 'Source',
  untilFurtherNotice: 'Until further notice',
  editsTitle: 'Operator edits',
} as const;

// Summary count words, in display order.
export const STATE_COUNT_LABEL: Record<DataStatus, string> = {
  current: 'current',
  stale: 'stale',
  conflicting: 'conflicting',
  missing: 'missing',
};

// Group headings in display order; general rows apply to every condition.
export const FACT_GROUP_LABEL: Record<ScenarioFamily | 'general', string> = {
  general: 'General',
  transmission: 'Transmission',
  high_frequency_minimum_generation: 'High frequency / minimum generation',
  snsp: 'SNSP',
};

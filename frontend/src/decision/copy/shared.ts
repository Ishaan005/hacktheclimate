// Labels shared by every part of the decision workspace.

import type { DataSourceKind, DataStatus, FactOrigin, PlanLabel, SafetyResult } from '../types';

export const RESULT_LABEL: Record<SafetyResult, string> = {
  pass: 'Pass',
  fail: 'Fail',
  unknown: 'Unknown',
};

export const PLAN_LABEL: Record<PlanLabel, string> = {
  actionable: 'Actionable',
  conditional: 'Conditional',
  unsafe: 'Unsafe',
  insufficient_evidence: 'Insufficient evidence',
};

export const SOURCE_KIND_LABEL: Record<DataSourceKind, string> = {
  live: 'Live',
  historical_demo: 'Historical demonstration',
  planning_case: 'Planning case',
  no_live_connection: 'No live connection',
};

export const DATA_STATUS_LABEL: Record<DataStatus, string> = {
  current: 'Current',
  stale: 'Stale',
  missing: 'Missing',
  conflicting: 'Conflicting',
};

export const ORIGIN_LABEL: Record<FactOrigin, string> = {
  measured: 'Measured',
  forecast: 'Forecast',
  inferred: 'Inferred',
  operator: 'Entered by operator',
};

export const NOT_ESTABLISHED = 'Not established';
export const STALE_NOTE = 'Out of date: the plan or its inputs changed. Rerun the assessment.';

// Adapter between the issue #61 workspace UI and POST /v1/workspace/assess.
// Backend values alone determine safety and outcomes. UI inputs describe a
// case or an operator alternative; they cannot assert an approved check.

import { siteById } from './sites';
import type { AssessmentRequest } from './api';
import type {
  ActionKind, ActionSafetyCheck, Assessment, DataStatus,
  Established, OutcomeState, Plan, SafetyCheck, SafetyResult, ScenarioFamily,
  SituationFact,
} from './types';

type BackendFact = {
  field: string; family: ScenarioFamily | 'general';
  value: number | string | boolean | null; unit: string | null;
  source: string | null; source_type: string | null;
  available_at: string | null; observed_at: string | null;
  issued_at: string | null; valid_at: string | null;
  state: DataStatus; reason: string | null;
  observations: Array<{ value: number | string | boolean | null; source: string }>;
  operator_edit: boolean;
};

type BackendCheck = {
  check_id: string; family: ScenarioFamily | 'action' | 'cross_family' | 'intake';
  action_step_id: string | null; status: 'PASS' | 'FAIL' | 'UNKNOWN';
  value: number | string | boolean | null; unit: string | null;
  effective_limit: number | string | boolean | null; margin: number | null;
  worst_time: string | null; worst_failure: string | null; source: string | null; reason: string;
};

type BackendBenefit = { value: number | null; unit: string | null; method: string | null; source: string | null; reason: string | null };
type BackendPlanStep = {
  step_id: string; action_id: string;
  role: 'main' | 'supporting' | 'parallel';
  instruction: string | null;
  asset_or_party: string | null; executor: string | null;
  permission_route: 'direct' | 'needs_clearance' | 'needs_acceptance';
  permission: 'confirmed' | 'pending' | 'denied' | 'unknown';
  permission_party: string | null;
  starts_at: string | null; effect_at: string | null; ends_at: string | null;
  limiting_location_delta_mw: number | null; depends_on: string[];
};
type BackendColumn = {
  plan: { steps: BackendPlanStep[] };
  safety: { status: 'PASS' | 'FAIL' | 'UNKNOWN'; reason: string; missing_checks: string[] };
  plan_label: 'Actionable' | 'Conditional' | 'Unsafe' | 'Insufficient evidence';
  checks: BackendCheck[];
  delivered_relief_mw: number | null;
  response_time_seconds: number | null;
  time_to_breach_seconds: number | null;
  worst_limit_margin: number | null;
  benefits: Record<string, BackendBenefit>;
};

export type BackendAssessment = {
  schema_version: 1; case_id: string; assessed_at: string;
  view: 'national' | 'site'; location: string | null; decision_time: string;
  window: { starts_at: string; ends_at: string };
  source_status: 'no_live_connection' | 'planning_case' | 'historical_demonstration' | 'live';
  bindings: Array<{ scenario_id: string; missing_fields: string[] }>;
  facts: BackendFact[];
  active_instructions: Array<{ instruction_id: string; starts_at: string; ends_at: string; evidence_reference: string }>;
  comparisons: Record<'current_plan' | 'no_new_instruction' | 'proposed_plan' | 'operator_alternative', BackendColumn>;
  evidence: {
    scenario_catalogue_source: string; scenario_catalogue_version: number;
    safety_policy_version: string | null; model_version: string | null;
    assumptions: string[]; missing_checks: string[];
    audit_id: string; audit_persisted: boolean; reason: string;
  };
};

const ACTION_IDS: Record<ActionKind, string> = {
  paired_redispatch: 'GENERATOR_REDISPATCH', switch_sectionalise: 'NETWORK_SWITCHING',
  return_equipment_early: 'OUTAGE_RETURN', local_storage_or_demand: 'STORAGE_CHARGE',
  wdt_limit: 'RENEWABLE_LIMIT', interconnector_transfer: 'INTERCONNECTOR_TRANSFER',
  fast_generation_reduction: 'RENEWABLE_LIMIT', emergency_hvdc: 'INTERCONNECTOR_TRANSFER',
  swap_lower_minimum_unit: 'UNIT_COMMITMENT', replace_reserve_provider: 'RESERVE_RAMP_ACTION',
  commit_for_upward_ramp: 'RESERVE_RAMP_ACTION', battery_charge_keep_service: 'STORAGE_CHARGE',
  snsp_interconnector: 'INTERCONNECTOR_TRANSFER', snsp_demand_release: 'FLEX_LOAD',
  snsp_all_island_wdt: 'RENEWABLE_LIMIT',
};

const BACKEND_ACTION_KINDS: Record<string, ActionKind> = {
  GENERATOR_REDISPATCH: 'paired_redispatch',
  NETWORK_SWITCHING: 'switch_sectionalise',
  OUTAGE_RETURN: 'return_equipment_early',
  FLEX_LOAD: 'local_storage_or_demand',
  STORAGE_CHARGE: 'local_storage_or_demand',
  RENEWABLE_LIMIT: 'wdt_limit',
  INTERCONNECTOR_TRANSFER: 'interconnector_transfer',
  UNIT_COMMITMENT: 'swap_lower_minimum_unit',
  RESERVE_RAMP_ACTION: 'replace_reserve_provider',
};

const FACT_LABELS: Record<string, string> = {
  active_instructions: 'Current instructions', limiting_equipment: 'Limiting equipment',
  normal_flow_mw: 'Normal route flow', normal_flow_limit_mw: 'Normal flow limit',
  post_failure_flow_mw: 'Post-failure flow', post_failure_limit_mw: 'Post-failure limit',
  credible_failure: 'Credible failure', measured_frequency_hz: 'Measured frequency',
  effective_high_frequency_limit_hz: 'Effective high-frequency limit',
  snsp_ratio_pct: 'All-island SNSP', effective_snsp_limit_pct: 'Effective SNSP limit',
  all_island_snsp: 'All-island SNSP', net_interconnector_transfer_mw: 'Net interconnector transfer (MW, + import)',
};

// Unit suffixes become a bracketed unit; grid terms keep their usual case.
const UNIT_SUFFIX: Record<string, string> = { mw: 'MW', mwh: 'MWh', pct: '%', hz: 'Hz', seconds: 's', minutes: 'min' };
const TERMS: Record<string, string> = { snsp: 'SNSP', rocof: 'RoCoF', hvdc: 'HVDC', wdt: 'WDT', tso: 'TSO', min: 'minimum' };

export function label(id: string): string {
  if (FACT_LABELS[id]) return FACT_LABELS[id];
  const words = id.split('_');
  const unit = UNIT_SUFFIX[words[words.length - 1]];
  if (unit) words.pop();
  if (words[0] === 'planning') words.splice(0, 1, 'Planning case:');
  const text = words.map((word) => TERMS[word] ?? word).join(' ');
  const sentence = text.charAt(0).toUpperCase() + text.slice(1);
  return unit ? `${sentence} (${unit})` : sentence;
}

// One wording for every value the assessment did not supply, so the
// comparison lists it once.
const NOT_VALIDATED = 'The assessment has not established this value.';

// File paths and exception text are for the log, not the operator. Each
// distinct detail is logged once.
const loggedDetails = new Set<string>();

export function operatorReason(reason: string | null): string | null {
  if (!reason) return reason;
  if (/errno|no such file|traceback|\/users\/|[a-z]:\\/i.test(reason)) {
    if (!loggedDetails.has(reason)) {
      loggedDetails.add(reason);
      console.error('Assessment detail:', reason);
    }
    return reason.toLowerCase().startsWith('planning')
      ? 'Planning-case inputs are not available on this server.'
      : 'An input needed for this check is not available on this server.';
  }
  return reason;
}

function nextHalfHour(now: Date): Date {
  const start = new Date(now);
  start.setUTCSeconds(0, 0);
  start.setUTCMinutes(now.getUTCMinutes() < 30 ? 30 : 0);
  if (now.getUTCMinutes() >= 30) start.setUTCHours(start.getUTCHours() + 1);
  return start;
}

function caseEvidence(request: AssessmentRequest, asOf: string) {
  const evidence: Array<Record<string, unknown>> = [];
  const add = (field: string, value: number | string | null, unit: string, source: string, availableAt: string) => {
    if (value === null || value === '') return;
    evidence.push({ field, value, unit, source_type: 'operator', source,
      source_version: 'workspace-ui-v1', available_at: availableAt, max_age_seconds: 86400 });
  };
  for (const condition of request.conditions) {
    if (condition.limitingAsset) add('limiting_equipment', condition.limitingAsset, '', 'Operator review', asOf);
    if (condition.reach) add('reach', condition.reach, '', 'Operator review', asOf);
    if (condition.outageType) add('outage_type', condition.outageType, '', 'Operator review', asOf);
    if (condition.timeSetting) add('now_or_forecast', condition.timeSetting, '', 'Operator review', asOf);
    if (condition.jurisdiction) add('jurisdiction', condition.jurisdiction, '', 'Operator review', asOf);
  }
  for (const fact of request.facts) {
    if (fact.origin !== 'operator' || fact.value === null) continue;
    // A correction replaces the reviewed intake value for this field. Sending
    // both as current would manufacture a source conflict on reassessment.
    for (let index = evidence.length - 1; index >= 0; index -= 1) {
      if (evidence[index].field === fact.id) evidence.splice(index, 1);
    }
    add(fact.id, fact.value, fact.unit ?? 'text', fact.source ?? 'Operator', asOf);
  }
  return evidence;
}

function backendPlan(plan: Plan | null) {
  return { steps: (plan?.steps ?? []).map((step) => {
    const start = step.startTime ? new Date(step.startTime) : null;
    const effect = step.effectTime ? new Date(step.effectTime) : null;
    const validStart = start && !Number.isNaN(start.getTime()) ? start : null;
    const validEffect = effect && !Number.isNaN(effect.getTime()) && (!validStart || effect >= validStart) ? effect : null;
    const end = validStart && step.durationMinutes !== null && step.durationMinutes > 0
      ? new Date(validStart.getTime() + step.durationMinutes * 60_000) : null;
    return {
      step_id: step.id, action_id: ACTION_IDS[step.kind],
      role: step.role, instruction: step.instruction,
      asset_or_party: step.executor || null, executor: step.executor || null,
      permission_route: step.permissionRoute,
      permission: step.permissionState === 'refused' ? 'denied' : step.permissionState,
      permission_party: step.permissionParty,
      starts_at: validStart?.toISOString() ?? null, effect_at: validEffect?.toISOString() ?? null,
      ends_at: end && (!validEffect || end >= validEffect) ? end.toISOString() : null,
      limiting_location_delta_mw: step.mwEffect, depends_on: step.dependsOn,
    };
  }) };
}

export function toBackendRequest(request: AssessmentRequest, now = new Date()) {
  const start = nextHalfHour(now);
  const end = new Date(start.getTime() + 24 * 60 * 60_000);
  const asOf = now.toISOString();
  const scenarioIds = [...new Set(request.conditions.map((condition) => condition.scenarioId))];
  return {
    decision_case: {
      case_id: `workspace-${request.description.trim().slice(0, 40) || 'case'}`,
      scenario_ids: scenarioIds, cause_unknown: scenarioIds.length === 0,
      location: request.view === 'site' ? siteById(request.siteId)?.name ?? request.siteId : 'All-island',
      asset_ids: [], as_of: asOf, starts_at: start.toISOString(), ends_at: end.toISOString(),
      existing_instructions: [],
    },
    description: request.description,
    conditions: request.conditions.map((condition) => ({
      scenario_id: condition.scenarioId,
      situation_key: condition.situationKey,
      reach: condition.reach,
      limiting_asset: condition.limitingAsset,
      outage_type: condition.outageType,
      time_setting: condition.timeSetting,
      snsp_drivers: condition.snspDrivers,
      jurisdiction: condition.jurisdiction,
    })),
    view: request.view, site_id: request.view === 'site' ? request.siteId : null,
    evidence: caseEvidence(request, asOf),
    proposed_plan: { steps: [] }, operator_alternative: backendPlan(request.alternative),
  };
}

function status(value: BackendCheck['status']): SafetyResult {
  return value.toLowerCase() as SafetyResult;
}

function display(value: number | string | boolean | null, unit: string | null): string | null {
  if (value === null) return null;
  return unit ? `${value} ${unit}` : String(value);
}

function factView(fact: BackendFact): SituationFact {
  const alternatives = fact.state === 'conflicting'
    ? fact.observations.map((item) => `${item.value} (${item.source})`).join('; ') : null;
  return { id: fact.field, label: label(fact.field),
    value: typeof fact.value === 'boolean' ? String(fact.value) : fact.value,
    unit: fact.unit, source: fact.source,
    timestamp: fact.valid_at ?? fact.observed_at ?? fact.issued_at ?? fact.available_at,
    // A missing fact has no origin: nothing supplied it.
    origin: fact.state === 'missing' && !fact.source_type ? null
      : fact.source_type === 'measurement' ? 'measured' : fact.source_type === 'forecast' ? 'forecast'
      : fact.source_type === 'operator' ? 'operator' : 'inferred',
    state: fact.state, family: fact.family, conflictNote: alternatives,
    editable: fact.state !== 'current' || fact.source_type !== 'measurement', editedFrom: null };
}

function checkView(check: BackendCheck): SafetyCheck {
  return { id: check.action_step_id ? `${check.action_step_id}:${check.check_id}` : check.check_id,
    label: label(check.check_id), family: check.family === 'action' || check.family === 'intake' ? 'cross_family' : check.family,
    value: display(check.value, check.unit), limit: display(check.effective_limit, check.unit),
    margin: display(check.margin, check.unit), worstTime: check.worst_time,
    worstFailure: check.worst_failure, source: check.source, result: status(check.status), reason: operatorReason(check.reason) ?? '' };
}

function established(item: BackendBenefit | undefined, unit: string, reason: string): Established {
  return { value: item?.value ?? null, lower: null, upper: null, unit: item?.unit ?? unit,
    method: item?.method ?? null, source: item?.source ?? null,
    notEstablishedReason: item?.value == null ? item?.reason ?? reason : null };
}

function outcome(column: OutcomeState['column'], value: BackendColumn, window: BackendAssessment['window'], available: boolean): OutcomeState {
  const reason = available ? null : 'No plan entered for this column.';
  const metric = (amount: number | null, unit: string) => established(
    amount === null ? undefined : { value: amount, unit, method: null, source: null, reason: '' }, unit,
    NOT_VALIDATED);
  return { column, available, unavailableReason: reason, windowStart: window.starts_at,
    windowEnd: window.ends_at, includesActiveInstructions: true, safety: status(value.safety.status),
    worstMargin: value.worst_limit_margin === null ? null : `${value.worst_limit_margin}`,
    deliveredReliefMw: metric(value.delivered_relief_mw, 'MW'),
    responseTimeMinutes: metric(value.response_time_seconds === null ? null : value.response_time_seconds / 60, 'min'),
    timeToBreachMinutes: metric(value.time_to_breach_seconds === null ? null : value.time_to_breach_seconds / 60, 'min'),
    constrainedMwh: established(value.benefits.constraint_mwh, 'MWh', 'Constraint not established'),
    curtailedMwh: established(value.benefits.curtailment_mwh, 'MWh', 'Curtailment not established') };
}

function planLabel(value: BackendColumn['plan_label']): Plan['label'] {
  return ({ Actionable: 'actionable', Conditional: 'conditional', Unsafe: 'unsafe',
    'Insufficient evidence': 'insufficient_evidence' } as const)[value];
}

function backendStep(step: BackendPlanStep, checks: BackendCheck[]) {
  const kind = BACKEND_ACTION_KINDS[step.action_id];
  if (!kind) return null;
  const start = step.starts_at ? new Date(step.starts_at) : null;
  const end = step.ends_at ? new Date(step.ends_at) : null;
  const durationMinutes = start && end && !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())
    ? Math.max(0, Math.round((end.getTime() - start.getTime()) / 60_000))
    : null;
  return {
    id: step.step_id,
    kind,
    role: step.role,
    instruction: step.instruction ?? label(step.action_id),
    executor: step.executor ?? step.asset_or_party ?? 'Unspecified executor',
    permissionRoute: step.permission_route,
    permissionState: step.permission === 'denied' ? 'refused' as const : step.permission,
    permissionParty: step.permission_party,
    startTime: step.starts_at,
    effectTime: step.effect_at,
    durationMinutes,
    mwEffect: step.limiting_location_delta_mw,
    dependsOn: step.depends_on,
    blockingCheckIds: checks
      .filter((check) => check.action_step_id === step.step_id && check.status !== 'PASS')
      .map((check) => `${step.step_id}:${check.check_id}`),
  };
}

function backendPlanView(
  value: BackendColumn,
  origin: Plan['origin'],
  name: string,
): Plan | null {
  if (!value.plan.steps.length) return null;
  const steps = value.plan.steps.map((step) => backendStep(step, value.checks)).filter((step) => step !== null);
  if (!steps.length) return null;
  return {
    id: origin === 'proposed' ? 'plan-proposed' : 'plan-operator',
    name,
    origin,
    steps,
    label: planLabel(value.plan_label),
    labelReason: operatorReason(value.safety.reason) ?? '',
  };
}

export function fromBackendAssessment(raw: BackendAssessment, request: AssessmentRequest): Assessment {
  const site = request.view === 'site' ? siteById(request.siteId) : undefined;
  const proposal = raw.comparisons.proposed_plan;
  const alternative = raw.comparisons.operator_alternative;
  const selected = proposal.plan.steps.length ? proposal : alternative.plan.steps.length ? alternative : raw.comparisons.no_new_instruction;
  const familyChecks = selected.checks.filter((check) => check.family === 'transmission' || check.family === 'high_frequency_minimum_generation' || check.family === 'snsp').map(checkView);
  const crossChecks = selected.checks.filter((check) => check.family === 'cross_family' || check.family === 'intake').map(checkView);
  const firstPerStep = new Set<string>();
  const actionChecks: ActionSafetyCheck[] = selected.checks.filter((check) => check.action_step_id !== null).map((check) => {
    const stepId = check.action_step_id!;
    const goNoGo = !firstPerStep.has(stepId);
    firstPerStep.add(stepId);
    return { ...checkView(check), stepId, goNoGo };
  });
  // Instructions in force have their own list, so they are not a fact row.
  const facts = raw.facts.filter((fact) => fact.field !== 'active_instructions').map(factView);
  const dataStatus: DataStatus = facts.some((fact) => fact.state === 'conflicting') ? 'conflicting'
    : facts.some((fact) => fact.state === 'stale') ? 'stale'
    : facts.some((fact) => fact.state === 'missing') ? 'missing' : 'current';
  const proposedPlan = backendPlanView(proposal, 'proposed', 'Backend proposal');
  const altPlan = backendPlanView(alternative, 'operator', request.alternative?.name ?? 'Operator alternative');
  const benefits = proposal.benefits;
  const reason = NOT_VALIDATED;
  return {
    validated: false,
    context: { view: request.view, location: request.view === 'site' ? site?.name ?? raw.location ?? 'Site not selected' : 'All-island',
      siteId: request.siteId, siteConnection: null, limitingRoute: null,
      currentTime: raw.decision_time, windowStart: raw.window.starts_at, windowEnd: raw.window.ends_at,
      sourceKind: raw.source_status === 'historical_demonstration' ? 'historical_demo' : raw.source_status,
      dataStatus },
    conditions: request.conditions,
    causeUnknown: raw.bindings.length ? null : {
      reason: selected.checks.find((check) => check.family === 'intake')?.reason ?? 'The assessment could not name a limiting cause in the locked scope.',
      factsNeeded: ['Limiting route or requirement', 'Measured or forecast value against its limit', 'Now or forecast, and the time window'],
    },
    facts,
    activeInstructions: raw.active_instructions.map((item) => ({ id: item.instruction_id,
      text: item.instruction_id, asset: 'Unspecified asset', issuedAt: item.starts_at,
      effectiveUntil: item.ends_at, source: item.evidence_reference })),
    edits: request.edits,
    overall: { result: status(selected.safety.status), reason: operatorReason(selected.safety.reason) ?? '',
      missingEvidence: selected.safety.missing_checks.map(label) },
    familyChecks, crossChecks, actionChecks,
    allIslandChecks: request.view === 'site' ? familyChecks.filter((check) => check.family !== 'transmission') : [],
    proposed: proposedPlan,
    alternative: altPlan,
    outcomes: [
      outcome('current', raw.comparisons.current_plan, raw.window, true),
      outcome('no_new_instruction', raw.comparisons.no_new_instruction, raw.window, true),
      outcome('proposed', proposal, raw.window, proposal.plan.steps.length > 0),
      outcome('operator_alternative', alternative, raw.window, alternative.plan.steps.length > 0),
    ],
    benefits: {
      avoidedDispatchDownMwh: established(benefits.avoided_dispatch_down_mwh, 'MWh', reason),
      siteRiskProbability: established(undefined, '%', reason),
      siteRiskExpectedMwh: established(undefined, 'MWh', reason),
      nationalContext: null,
      netSystemResourceCostEur: { ...established(benefits.system_resource_cost_eur, 'EUR', reason), perspective: null },
      grossMarketOpportunityEur: established(benefits.gross_market_opportunity_eur, 'EUR', reason),
      netFinancialValueEur: { ...established(benefits.net_financial_value_eur, 'EUR', reason), perspective: null },
      carbonEffectTco2e: established(benefits.carbon_tco2e, 'tCO2e', reason),
    },
    evidence: {
      inputs: facts.filter((fact) => fact.value !== null).map((fact) => ({ label: fact.label,
        source: fact.source ?? 'Unspecified', timestamp: fact.timestamp, editedByOperator: fact.origin === 'operator' })),
      ruleVersion: raw.evidence.safety_policy_version,
      modelVersions: raw.evidence.model_version ? [raw.evidence.model_version] : [],
      limitsUsed: [], credibleFailuresUsed: [], actionDecisions: [],
      assumptions: raw.evidence.assumptions.map((item) => operatorReason(item) ?? item),
      uncertainty: [operatorReason(raw.evidence.reason) ?? '', raw.evidence.audit_persisted ? '' : 'Assessment fingerprint is not a stored audit record.'].filter(Boolean),
      missingChecks: raw.evidence.missing_checks.map(label),
      assessedAt: raw.assessed_at, auditId: raw.evidence.audit_persisted ? raw.evidence.audit_id : null,
      feedFreshness: [],
    },
  };
}

export function isBackendAssessment(value: unknown): value is BackendAssessment {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<BackendAssessment>;
  return item.schema_version === 1 && Array.isArray(item.facts) && !!item.comparisons
    && !!item.comparisons.no_new_instruction && !!item.comparisons.proposed_plan
    && !!item.comparisons.operator_alternative && !!item.evidence;
}

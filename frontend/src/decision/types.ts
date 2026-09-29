// View model for the operator decision workspace (UI brief, 29 September
// 2026: docs/UI_BRIEF_2026-09-29.md). The backend sends one assessment; the
// UI displays it and never computes a safety result itself. Every value that
// can be missing is nullable: null means not supplied, never zero.

// ---- Locked scope (config/decision_scenarios_v1.json) ----

export type ScenarioId = 'T1' | 'T2' | 'T3' | 'T4' | 'H1' | 'H2' | 'H3' | 'H4' | 'SNSP';

export type ScenarioFamily = 'transmission' | 'high_frequency_minimum_generation' | 'snsp';

// Details recorded with a condition. They refine the condition; they are not
// extra cases.
export type TransmissionReach = 'local_area' | 'shared_route' | 'wide_group';
export type OutageType = 'planned' | 'forced';
export type TimeSetting = 'now' | 'forecast';

// One limiting condition. More than one can bind at once.
export type BindingCondition = {
  scenarioId: ScenarioId;
  // Plain-language situation picked or matched, e.g. 'lost_interconnector_export'.
  situationKey: string | null;
  reach: TransmissionReach | null;
  limitingAsset: string | null;
  outageType: OutageType | null;
  timeSetting: TimeSetting | null;
  // SNSP only: what moved the ratio toward the limit. Several can apply.
  snspDrivers: SnspDriver[];
  // H2 only.
  jurisdiction: Jurisdiction | null;
  // Set once the operator accepts the match before assessment.
  confirmedByOperator: boolean;
};

export type Jurisdiction = 'ireland' | 'northern_ireland' | 'both';

export type SnspDriver = 'renewables_up' | 'demand_down' | 'imports_up' | 'exports_down';

// Intake state, not a scenario: the app cannot yet name the limiting cause.
export type CauseUnknown = {
  reason: string;
  factsNeeded: string[];
};

// ---- Top bar ----

export type ViewMode = 'national' | 'site';

// Never show a demonstration as live.
export type DataSourceKind = 'live' | 'historical_demo' | 'planning_case' | 'no_live_connection';

export type DataStatus = 'current' | 'stale' | 'missing' | 'conflicting';

export type WorkspaceContext = {
  view: ViewMode;
  // Site name in site view; 'All-island' in national view.
  location: string;
  siteId: string | null;
  // Connection and limiting route, site view only.
  siteConnection: string | null;
  limitingRoute: string | null;
  currentTime: string;
  windowStart: string;
  windowEnd: string;
  sourceKind: DataSourceKind;
  dataStatus: DataStatus;
};

// ---- Situation table ----

export type FactOrigin = 'measured' | 'forecast' | 'inferred' | 'operator';

export type SituationFact = {
  id: string;
  label: string;
  value: number | string | null;
  unit: string | null;
  source: string | null;
  timestamp: string | null;
  origin: FactOrigin;
  state: DataStatus;
  // Which family table this row belongs to; 'general' rows show for all.
  family: ScenarioFamily | 'general';
  // Conflicting rows name the other value.
  conflictNote: string | null;
  // Rows that come from a reliable current feed are not asked of the operator.
  editable: boolean;
  // Previous value when the operator edited it.
  editedFrom: number | string | null;
};

// Current operating plan and instructions already in force.
export type ActiveInstruction = {
  id: string;
  text: string;
  asset: string;
  issuedAt: string;
  effectiveUntil: string | null;
  source: string;
};

export type OperatorEdit = {
  factId: string;
  // Fact label at the time of the edit, so the evidence reads without IDs.
  label: string;
  from: number | string | null;
  to: number | string | null;
  at: string;
};

// ---- Safety ----

export type SafetyResult = 'pass' | 'fail' | 'unknown';

export type SafetyCheck = {
  id: string;
  label: string;
  family: ScenarioFamily | 'cross_family';
  // Measured or studied value; text keeps the unit, e.g. '412 MW'.
  value: string | null;
  limit: string | null;
  margin: string | null;
  worstTime: string | null;
  // Transmission only: worst credible equipment failure.
  worstFailure: string | null;
  source: string | null;
  result: SafetyResult;
  reason: string;
};

// Grouped under the action step it belongs to. The first item is the
// go/no-go check and sits at the top of the expanded row.
export type ActionSafetyCheck = SafetyCheck & {
  stepId: string;
  goNoGo: boolean;
};

export type OverallSafety = {
  result: SafetyResult;
  reason: string;
  // Named when the result is unknown.
  missingEvidence: string[];
};

// ---- Plans ----

export type ActionKind =
  // Transmission
  | 'paired_redispatch'
  | 'switch_sectionalise'
  | 'return_equipment_early'
  | 'local_storage_or_demand'
  | 'wdt_limit'
  | 'interconnector_transfer'
  // High frequency / minimum generation
  | 'fast_generation_reduction'
  | 'emergency_hvdc'
  | 'swap_lower_minimum_unit'
  | 'replace_reserve_provider'
  | 'commit_for_upward_ramp'
  | 'battery_charge_keep_service'
  // SNSP
  | 'snsp_interconnector'
  | 'snsp_demand_release'
  | 'snsp_all_island_wdt';

// direct: the operator can instruct it. needs_clearance / needs_acceptance:
// another party must clear or accept first.
export type PermissionRoute = 'direct' | 'needs_clearance' | 'needs_acceptance';
export type PermissionState = 'confirmed' | 'pending' | 'refused' | 'unknown';

export type PlanStep = {
  id: string;
  kind: ActionKind;
  role: 'main' | 'supporting' | 'parallel';
  // What exactly would be instructed.
  instruction: string;
  executor: string;
  permissionRoute: PermissionRoute;
  permissionState: PermissionState;
  // Party that must clear or accept, when not direct.
  permissionParty: string | null;
  startTime: string | null;
  effectTime: string | null;
  durationMinutes: number | null;
  // MW change at the limiting location. Signed: negative relieves a flow.
  mwEffect: number | null;
  // IDs of steps that must happen first.
  dependsOn: string[];
  // Checks that still block this step, by check ID.
  blockingCheckIds: string[];
};

export type PlanLabel = 'actionable' | 'conditional' | 'unsafe' | 'insufficient_evidence';

export type Plan = {
  id: string;
  name: string;
  origin: 'proposed' | 'operator';
  steps: PlanStep[];
  // Backend label. The UI re-derives it with planLabel() and shows the more
  // cautious of the two.
  label: PlanLabel;
  labelReason: string;
};

// ---- Comparison ----

export type ComparisonColumn = 'current' | 'no_new_instruction' | 'proposed' | 'operator_alternative';

// A number with its method, or the reason it is not established.
export type Established = {
  value: number | null;
  lower: number | null;
  upper: number | null;
  unit: string;
  method: string | null;
  source: string | null;
  // Set when value is null.
  notEstablishedReason: string | null;
};

export type OutcomeState = {
  column: ComparisonColumn;
  // Null when this plan state has not been evaluated (e.g. no operator
  // alternative yet).
  available: boolean;
  unavailableReason: string | null;
  windowStart: string;
  windowEnd: string;
  // Includes active instructions.
  includesActiveInstructions: boolean;
  safety: SafetyResult;
  worstMargin: string | null;
  deliveredReliefMw: Established;
  responseTimeMinutes: Established;
  timeToBreachMinutes: Established;
  constrainedMwh: Established;
  curtailedMwh: Established;
};

export type Benefits = {
  // No-new-instruction MWh minus proposed-plan MWh.
  avoidedDispatchDownMwh: Established;
  siteRiskProbability: Established;
  siteRiskExpectedMwh: Established;
  // Present only as context when a site model is not validated.
  nationalContext: string | null;
  netSystemResourceCostEur: Established & { perspective: string | null };
  grossMarketOpportunityEur: Established;
  netFinancialValueEur: Established & { perspective: string | null };
  carbonEffectTco2e: Established;
};

// ---- Evidence ----

export type EvidenceInput = {
  label: string;
  source: string;
  timestamp: string | null;
  editedByOperator: boolean;
};

export type ActionDecision = {
  stepId: string | null;
  kind: ActionKind;
  decision: 'included' | 'rejected' | 'conditional';
  reason: string;
};

export type Evidence = {
  inputs: EvidenceInput[];
  ruleVersion: string | null;
  modelVersions: string[];
  limitsUsed: string[];
  credibleFailuresUsed: string[];
  actionDecisions: ActionDecision[];
  assumptions: string[];
  uncertainty: string[];
  missingChecks: string[];
  assessedAt: string | null;
  auditId: string | null;
  feedFreshness: { feed: string; status: DataStatus; asOf: string | null }[];
};

// ---- One assessment ----

export type Assessment = {
  context: WorkspaceContext;
  conditions: BindingCondition[];
  causeUnknown: CauseUnknown | null;
  facts: SituationFact[];
  activeInstructions: ActiveInstruction[];
  edits: OperatorEdit[];
  overall: OverallSafety;
  familyChecks: SafetyCheck[];
  // Other affected limits, e.g. battery capacity promised for frequency.
  crossChecks: SafetyCheck[];
  actionChecks: ActionSafetyCheck[];
  // All-island checks that still matter in site view.
  allIslandChecks: SafetyCheck[];
  proposed: Plan | null;
  alternative: Plan | null;
  outcomes: OutcomeState[];
  benefits: Benefits;
  evidence: Evidence;
  // Validated backend assessment; false for fixture/demo content.
  validated: boolean;
};

// Response types for the operator screen.
//
// Planning scenario: mirrors the report written by
// backend/app/network_scenarios.py `compare_network_scenarios` plus the
// `outage_review` added by scripts/compare_network_scenarios.py (branch
// codex/network-issues-9-12). Only the fields the UI reads are typed; the
// real report carries more (all flows, islands, bus angles).
//
// National forecast and the combined envelope: PROPOSED. No backend exists
// yet (issues #8 and #14). Field names follow the wording of issue #14 and
// must be updated when that endpoint is built.

export type Unavailable<T extends string> = {
  output_type: T;
  status: 'unavailable';
  reason: string;
};

// ---- National forecast (proposed, issues #7, #8, #13, #14) ----
// Target is national constraint_mwh only, kept separate from system-wide
// curtailment (#8). Each interval records its decision time and horizon (#7).

export type ForecastInterval = {
  target_timestamp: string;
  decision_timestamp: string;
  horizon_hours: number;
  event_probability: number | null;
  expected_constraint_mwh: number | null;
  expected_constraint_mwh_lower: number | null;
  expected_constraint_mwh_upper: number | null;
};

// Weather comes from forecasts issued before the decision time (GFS archive
// for backtests, ECMWF open data live). Demand is a past-only lag, never a
// same-period actual (#7).
export type DecisionContextInterval = {
  target_timestamp: string;
  wind_speed_100m_ms: number | null;
  solar_radiation_w_m2: number | null;
  demand_lag_mw: number | null;
};

// Chronological evaluation summary (#8). A no-improvement result is reported
// as beats_baseline = false, not hidden.
export type ForecastEvaluation = {
  calibration_status: 'calibrated' | 'uncalibrated' | 'unknown';
  test_period: string | null;
  event_prevalence: number | null;
  pr_auc: number | null;
  interval_coverage: number | null;
  interval_nominal: number | null;
  beats_baseline: boolean | null;
  baseline: string | null;
  note: string | null;
};

export type SourceStatus = 'current' | 'stale' | 'unavailable';

export type DataSource = {
  source: string;
  vintage: string | null;
  retrieved_at: string | null;
  // Set by the API from each source's freshness rule (#13); the UI never infers it.
  status?: SourceStatus;
  attribution?: string | null;
  note: string | null;
};

export type NationalForecast = {
  output_type: 'forecast';
  status: 'ok';
  model_version: string;
  target: 'constraint_mwh';
  event_definition: string;
  issued_at: string;
  intervals: ForecastInterval[];
  decision_context: DecisionContextInterval[];
  evaluation: ForecastEvaluation;
  sources: DataSource[];
};

// ---- Planning scenario (real report fields) ----

export type AssetType = 'branch' | 'transformer';

export type AssetRef = {
  asset_type: AssetType;
  asset_id: string;
};

export type SolverStatus = 'ok' | 'islanded' | 'unsolved';

export type ScenarioFlow = AssetRef & {
  from_bus: number | string;
  to_bus: number | string;
  flow_mw: number;
  rating_mva: number | null;
  dc_loading_pct_proxy: number | null;
  dc_headroom_mw_unity_pf_proxy: number | null;
};

export type ScenarioRun = {
  status: SolverStatus;
  reason: string | null;
  flows: ScenarioFlow[];
};

export type RunName = 'intact' | 'planned_outage' | 'selected_n_minus_one';

export type FlowDelta = AssetRef & {
  intact_flow_mw: number | null;
  scenario_flow_mw: number | null;
  delta_flow_mw: number | null;
  state: 'online' | 'removed' | 'added';
};

export type CaseProvenance = {
  source_url: string;
  source_member: string;
  source_sha256: string;
  season: string;
  study_year: number;
  scenario_date: string;
  pss_e_version: number;
  scenario_label: string;
  source_note: string;
};

export type OutageReview = {
  sources: {
    annual: { url: string; http_last_modified: string };
    short_term: { url: string; http_last_modified: string };
  };
  annual: {
    outage_id: string;
    equipment_description: string;
    status: string;
    start_date: string | null;
    finish_date: string | null;
    source_row: number;
  };
  short_term: {
    outage_id: string;
    plant: string;
    status: string;
    source_row: number;
  };
  network_match: {
    decision: 'reviewed_scenario_candidate' | 'candidate_requires_manual_review' | 'unresolved';
    confidence?: string;
    reason?: string;
    state_warning?: string;
  };
};

export type ScenarioReport = {
  scenario_label: string;
  case_type: string;
  case_provenance: CaseProvenance;
  rating_basis: string;
  outage_reference: string;
  contingency_reference: string;
  planned_outage: AssetRef;
  contingency: AssetRef;
  monitored: AssetRef;
  monitor_by_run: Record<RunName, ScenarioFlow | null>;
  runs: Record<RunName, ScenarioRun>;
  flow_deltas_from_intact: Record<'planned_outage' | 'selected_n_minus_one', FlowDelta[] | null>;
  flow_deltas_from_planned_outage: FlowDelta[] | null;
  limitations: string[];
  outage_review: OutageReview;
  // Proposed (#15): not produced by compare_network_scenarios yet.
  affected_corridor?: string | null;
};

// Proposed wrapper so the combined API can tag the output type (issue #14).
export type PlanningScenario = {
  output_type: 'planning_scenario';
  status: 'ok';
  report: ScenarioReport;
};

// ---- Combined response (proposed, issue #14) ----

export type ReviewedOutageOption = {
  outage_id: string;
  equipment_description: string;
};

export type OperatorView = {
  forecast: NationalForecast | Unavailable<'forecast'>;
  scenario: PlanningScenario | Unavailable<'planning_scenario'> | null;
  decision?: NetworkDecision;
};

export type SafetyStatus = 'PASS' | 'FAIL' | 'UNKNOWN';

export type SafetyCheck = {
  status: SafetyStatus;
  reason: string;
  evidence: string | null;
};

export type SafetyResult = {
  overall: SafetyStatus;
  recommendable: boolean;
  thermal: SafetyCheck;
  islanding: SafetyCheck;
  snsp: SafetyCheck;
  voltage: SafetyCheck;
  inertia: SafetyCheck;
  rocof: SafetyCheck;
};

export type NetworkForecastRow = {
  valid_time: string;
  constraint_probability: number;
  expected_constraint_mwh: number;
  network: {
    scenario: string;
    worst_asset: string | null;
    max_dc_loading_proxy_pct: number | null;
    security_event: boolean;
    safety: SafetyResult;
  };
};

export type ScreenedAction = {
  action_id: string;
  power_mw: number;
  safety_overall: SafetyStatus;
  modeled_capture_upper_bound_mwh: number;
  expected_avoided_constraint_mwh: number | null;
};

export type NetworkDecision = {
  rows: NetworkForecastRow[];
  network: { case_scenario_date: string | null; planned_outage: AssetRef; scope: string };
  actions: ScreenedAction[];
  recommendation: null;
  health: {
    status: string;
    forecast_issue_time: string;
    forecast_source: string;
    missing_inputs: string[];
    unsupported_safety_checks: string[];
    recommendation_reason: string;
  };
};

// ---- Scenario workspace (UX plan phase 1) ----
// View model for Scenario → Binding condition → Recommended action → New
// outcome. Illustrative fixtures and the live operator view both map into it,
// so no component reads a backend shape directly.

export type GuardrailStatus = 'within_modelled_limit' | 'breach' | 'unknown';

// Safety constraints checked for every scenario. transmission_line covers
// line loading against rating; thermal_capacity covers transformers and other
// substation equipment. scope says whether the effect stays in the region or
// spreads grid-wide. min_generation covers the minimum number of synchronous
// units and the over-frequency risk at low demand.
export type GuardrailName =
  | 'transmission_line'
  | 'thermal_capacity'
  | 'snsp'
  | 'scope'
  | 'min_generation';

export type Guardrail = {
  name: GuardrailName;
  baseline: GuardrailStatus;
  postAction: GuardrailStatus;
  margin: string | null;
  timestamp: string | null;
  note: string | null;
};

export type BindingCondition = {
  type: string;
  metric: string;
  location: string | null;
  margin: string | null;
  status: GuardrailStatus;
};

// Core MVP actions from #21. Voltage and stability support are expanded MVP;
// interconnector changes are out of scope.
export type ActionFamily =
  | 'storage_charging'
  | 'flexible_demand'
  | 'generator_redispatch'
  | 'outage_review';

// Conditional: depends on a check or confirmation not yet made.
export type Executability = 'executable' | 'conditional';

// ---- Family-specific action detail (UX plan phase 2, #21 metric tables) ----
// Every field is nullable: null means the solver did not supply it, and the
// UI shows it as not available, never as zero.

export type StorageChargingDetails = {
  stateOfChargePct: number | null;
  minStateOfChargePct: number | null;
  maxStateOfChargePct: number | null;
  chargingTargetMw: number | null;
  availableChargingMwh: number | null;
  rampRateMwPerMin: number | null;
  roundTripEfficiencyPct: number | null;
  reboundRequirement: string | null;
  chargingCostEur: number | null;
  lossCostEur: number | null;
  degradationCostEur: number | null;
};

export type DemandDirection = 'increase' | 'decrease';

export type FlexibleDemandDetails = {
  direction: DemandDirection | null;
  changeMw: number | null;
  availableMwh: number | null;
  demandBaselineMw: number | null;
  activationDelayMinutes: number | null;
  maxDurationMinutes: number | null;
  // MW of constraint relief per MW of demand moved.
  constraintReliefPerMw: number | null;
  reboundRequirement: string | null;
  activationCostEur: number | null;
  reboundCostEur: number | null;
};

export type GeneratorRedispatchDetails = {
  currentMw: number | null;
  targetMw: number | null;
  rampRateMwPerMin: number | null;
  minStableGenerationMw: number | null;
  maxOutputMw: number | null;
  startStopRestrictions: string | null;
  servicesRetained: string[] | null;
  servicesLost: string[] | null;
  redispatchCostEur: number | null;
};

export type OutageReviewDetails = {
  outageId: string | null;
  equipmentDescription: string | null;
  scheduledStart: string | null;
  scheduledEnd: string | null;
  publicationDate: string | null;
  outageStatus: string | null;
  reviewedModelAsset: string | null;
  assetMatchConfidence: string | null;
  alternativeWindow: string | null;
  overlappingOutages: string[] | null;
  additionalExposureMwh: number | null;
  financialExposureEur: number | null;
};

// The family decides which detail shape the action carries.
export type ActionFamilyDetails =
  | { family: 'storage_charging'; details: StorageChargingDetails }
  | { family: 'flexible_demand'; details: FlexibleDemandDetails }
  | { family: 'generator_redispatch'; details: GeneratorRedispatchDetails }
  | { family: 'outage_review'; details: OutageReviewDetails };

// One step the operator takes to carry out the action, in order. `time` is
// null when the step has no fixed time, e.g. a confirmation.
export type ActionStep = {
  time: string | null;
  text: string;
};

export type RecommendedAction = ActionFamilyDetails & {
  assetName: string;
  location: string;
  currentState: string;
  targetState: string;
  issueTime: string;
  startTime: string;
  targetTime: string;
  effectiveUntil: string;
  earliestExecution: string | null;
  executability: Executability;
  steps: ActionStep[];
};

// Per-state values shown side by side. Null means unknown, never zero.
export type OutcomeState = {
  securityResult: GuardrailStatus;
  dispatchDownWasteMwh: number | null;
};

// Values that only exist because an action is taken.
export type ActionImpact = {
  grossMarketOpportunityEur: number | null;
  netFinancialValueEur: number | null;
  estimatedAvoidedEmissionsTco2e: number | null;
};

export type ScenarioSource = 'illustrative' | 'live';
// placeholder workspace scenario
export type WorkspaceScenario = {
  id: string;
  title: string;
  intervalStart: string;
  intervalEnd: string;
  source: ScenarioSource;
  modelRunAt: string | null;
  summary: string;
  // Extra words the situation matcher should recognise for this scenario.
  keywords: string[];
  binding: BindingCondition | null;
  action: RecommendedAction | null;
  noActionReason: string | null;
  baseline: OutcomeState;
  postAction: OutcomeState | null;
  impact: ActionImpact | null;
  guardrails: Guardrail[];
};

// ---- Solver follow-up questions ----
// When the description is not enough, the solver asks the operator before it
// returns a scenario. Each question names its input kind so the UI can render
// it without knowing the question in advance.

export type ChoiceOption = {
  value: string;
  label: string;
};

type QuestionBase = {
  // Stable within one request; answers refer back to it.
  id: string;
  prompt: string;
  helpText: string | null;
  required: boolean;
};

export type TextQuestion = QuestionBase & {
  kind: 'text';
  placeholder: string | null;
  maxLength: number | null;
};

export type SingleChoiceQuestion = QuestionBase & {
  kind: 'single_choice';
  options: ChoiceOption[];
};

export type MultiChoiceQuestion = QuestionBase & {
  kind: 'multi_choice';
  options: ChoiceOption[];
  minSelected: number | null;
  maxSelected: number | null;
};

// Rendered as a slider with a matching number field.
export type NumberQuestion = QuestionBase & {
  kind: 'number';
  min: number;
  max: number;
  step: number;
  unit: string | null;
  defaultValue: number | null;
};

export type ClarificationQuestion = TextQuestion | SingleChoiceQuestion | MultiChoiceQuestion | NumberQuestion;

export type ClarificationRequest = {
  // Why the solver is asking, in operator language.
  reason: string;
  questions: ClarificationQuestion[];
};

// Null means the operator left an optional question unanswered.
export type ClarificationAnswerValue = string | string[] | number | null;

// Question IDs are only unique within one round, so an answer names its
// round too: round 2 may reuse an ID from round 1 without replacing it.
export type ClarificationAnswer = {
  round: number;
  questionId: string;
  value: ClarificationAnswerValue;
};

// One request to the solver. Follow-up rounds resend the original
// description with every answer so far; `threadId` lets a stateful backend
// keep its own conversation instead.
export type SolverRequest = {
  description: string;
  threadId: string | null;
  answers: ClarificationAnswer[];
  // The reviewed case as text (description plus confirmed facts and their
  // sources). Set once the operator has checked the facts; the live solver
  // reads it instead of the bare description.
  caseSummary?: string;
};

// What the situation solver can return. The LLM chooses the output type from
// the operator's description; `target` is a UTC half-hour, 'YYYY-MM-DDTHH:MM'.
export type SolverResult =
  | { kind: 'scenario'; scenario: WorkspaceScenario }
  | { kind: 'dispatch_down_risk'; target: string }
  | { kind: 'clarification'; threadId: string | null; clarification: ClarificationRequest }
  // Free-text answer from the LangGraph assistant (POST /v1/chat). `target`
  // is set when the reply is about dispatch-down, so the real forecast view
  // can sit beside it.
  | { kind: 'assistant_reply'; reply: AssistantReply; target: string | null };

// One LangGraph node that ran during a chat turn, in order.
export type TraceStep = {
  node: string;
  detail: string;
};

export type AssistantReply = {
  threadId: string;
  text: string;
  toolsUsed: string[];
  model: string;
  // The path this turn actually took through the graph; empty from an older API.
  trace: TraceStep[];
};

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

export type GuardrailName = 'voltage' | 'thermal' | 'snsp' | 'inertia' | 'frequency';

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

export type ActionFamily =
  | 'generator_setpoint'
  | 'commitment_change'
  | 'storage_charging'
  | 'reactive_control'
  | 'renewable_limit'
  | 'interconnector_request';

// Direct dispatch is executable; an interconnector request stays unconfirmed
// until the counterparty confirms it.
export type Executability = 'executable' | 'conditional' | 'unconfirmed';

export type RecommendedAction = {
  family: ActionFamily;
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

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
};

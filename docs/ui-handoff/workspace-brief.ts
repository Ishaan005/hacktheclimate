// POST /v1/workspace/assess. UTC timestamps are ISO 8601 strings.
export type WorkspaceFactState = 'current' | 'stale' | 'missing' | 'conflicting' | 'modeled';
export type WorkspaceCheckState = 'PASS' | 'FAIL' | 'UNKNOWN';
export type WorkspacePlanLabel = 'Actionable' | 'Conditional' | 'Unsafe' | 'Insufficient evidence';
export type WorkspaceView = 'national' | 'site';

export interface WorkspacePlanStep {
  step_id: string;
  action_id: string;
  asset_or_party?: string | null;
  executor?: string | null;
  permission?: 'confirmed' | 'pending' | 'denied' | 'unknown';
  starts_at?: string | null;
  effect_at?: string | null;
  ends_at?: string | null;
  limiting_location_delta_mw?: number | null;
  depends_on?: string[];
}

export interface WorkspaceAssessmentRequest {
  decision_case: {
    case_id: string;
    scenario_ids: string[];
    cause_unknown?: boolean;
    location?: string | null;
    asset_ids?: string[];
    as_of: string;
    starts_at: string;
    ends_at: string;
    existing_instructions?: Array<{
      instruction_id: string;
      starts_at: string;
      ends_at: string;
      evidence_reference: string;
      included_in_forecast: boolean;
      constraint_delta_mwh_per_interval?: number | null;
      curtailment_delta_mwh_per_interval?: number | null;
    }>;
  };
  view?: WorkspaceView;
  site_id?: string | null;
  evidence?: Array<{
    field: string;
    value: number | string | boolean | null;
    unit: string;
    source_type: 'operator' | 'measurement' | 'forecast' | 'planning_model';
    source: string;
    source_version: string;
    available_at?: string | null;
    observed_at?: string | null;
    issued_at?: string | null;
    valid_at?: string | null;
    max_age_seconds?: number | null;
  }>;
  proposed_plan?: { steps: WorkspacePlanStep[] };
  operator_alternative?: { steps: WorkspacePlanStep[] };
}

export interface WorkspaceFact {
  field: string;
  family: 'transmission' | 'high_frequency_minimum_generation' | 'snsp' | 'general';
  value: number | string | boolean | null;
  unit: string | null;
  source: string | null;
  source_version: string | null;
  source_type: string | null;
  available_at: string | null;
  observed_at: string | null;
  issued_at: string | null;
  valid_at: string | null;
  state: WorkspaceFactState;
  reason: string | null;
  observations: WorkspaceAssessmentRequest['evidence'];
  operator_edit: boolean;
}

export interface WorkspaceCheck {
  check_id: string;
  family: string;
  action_step_id: string | null;
  status: WorkspaceCheckState;
  value: number | string | boolean | null;
  unit: string | null;
  effective_limit: number | string | boolean | null;
  margin: number | string | null;
  worst_time: string | null;
  worst_failure: string | null;
  source: string | null;
  reason: string;
}

export interface WorkspaceBenefit {
  value: number | null;
  unit: string | null;
  method: string | null;
  uncertainty: string | null;
  source: string | null;
  reason: string;
}

export interface WorkspaceComparison {
  state: 'current_plan' | 'no_new_instruction' | 'proposed_plan' | 'operator_alternative';
  window: { starts_at: string; ends_at: string };
  plan: { steps: WorkspacePlanStep[] };
  active_instructions: WorkspaceAssessmentRequest['decision_case']['existing_instructions'];
  permission_state: 'confirmed' | 'pending' | 'denied' | 'unknown';
  safety: { status: WorkspaceCheckState; reason: string; missing_checks: string[] };
  plan_label: WorkspacePlanLabel;
  checks: WorkspaceCheck[];
  delivered_relief_mw: number | null;
  response_time_seconds: number | null;
  time_to_breach_seconds: number | null;
  worst_limit_margin: number | null;
  benefits: Record<string, WorkspaceBenefit>;
}

export interface WorkspaceAssessment {
  schema_version: 1;
  case_id: string;
  revision: string;
  assessment_id: string;
  assessed_at: string;
  view: WorkspaceView;
  location: string | null;
  decision_time: string;
  window: { starts_at: string; ends_at: string };
  source_status: 'no_live_connection' | 'planning_case' | 'historical_demonstration' | 'live';
  data_status: string;
  bindings: Array<{
    scenario_id: string;
    name: string;
    family: string;
    classification_verified: boolean;
    missing_fields: string[];
  }>;
  facts: WorkspaceFact[];
  national_constraint_context: string | null;
  active_instructions: WorkspaceComparison['active_instructions'];
  comparisons: Record<WorkspaceComparison['state'], WorkspaceComparison>;
  evidence: {
    scenario_catalogue_source: string;
    scenario_catalogue_version: number;
    safety_policy_version: string | null;
    model_version: string | null;
    assumptions: string[];
    missing_checks: string[];
    audit_id: string;
    audit_persisted: boolean;
    reason: string;
  };
}

/** Current historical/replay timestamps are UTC strings without a Z suffix. */
export type UtcTimestamp = string

export interface HealthResponse {
  status: 'ok'
  canonical_data_exists: boolean
}

export interface PressureRow {
  timestamp: UtcTimestamp
  load_mw: number | null
  wind_onshore_mw: number | null
  solar_mw: number | null
  renewable_vre_share: number | null
  residual_load_mw: number | null
  sem_price_currency_per_mwh: number | null
  pressure_proxy: number | null
}

export interface DispatchDownRow {
  timestamp: UtcTimestamp
  dispatch_down_total_mwh: number | null
  constraint_mwh: number | null
  curtailment_mwh: number | null
  wind_dispatch_down_total_mwh: number | null
  solar_dispatch_down_total_mwh: number | null
  eirgrid_snsp_pct: number | null
  eirgrid_ie_demand_mw: number | null
  eirgrid_ie_wind_availability_mw: number | null
  eirgrid_ewic_ic_mw: number | null
  eirgrid_greenlink_ic_mw: number | null
  sem_price_currency_per_mwh: number | null
}

export interface AbsorptionRequest {
  start_target: UtcTimestamp
  intervals: number
  assets: Array<{
    name: string
    max_power_mw: number
    energy_required_mwh: number
    available: boolean[]
  }>
}

export interface AbsorptionResponse {
  scenario: 'retrospective_1h_operational'
  assumption: string
  interval_hours: number
  predicted_dispatch_down_mwh: number
  observed_dispatch_down_mwh: number
  schedule: {
    schedule_mw: Record<string, number[]>
    absorbed_mwh: number
    available_surplus_mwh: number
    capture_rate: number
  }
  intervals: Array<{
    target_timestamp: UtcTimestamp
    input_timestamp: UtcTimestamp
    event_probability_gt_5_mwh: number
    predicted_dispatch_down_mwh: number
    observed_dispatch_down_mwh: number
  }>
}

export interface NetworkForecastRow {
  valid_time: UtcTimestamp
  constraint_probability: number
  expected_constraint_mwh: number
  network: {
    scenario: string
    worst_asset: string | null
    max_dc_loading_proxy_pct: number | null
    minimum_headroom_proxy_mw: number | null
    worst_contingency: string | null
    worst_contingency_type: string | null
    n_assets_above_80pct: number | null
    scenarios: Record<string, {
      status: string
      operable_state: boolean
      worst_asset: string | null
      max_dc_loading_proxy_pct: number | null
      minimum_headroom_proxy_mw: number | null
      n_assets_above_80pct: number | null
    } | null>
    screened_contingency_count: number
    screened_islanding_contingencies: string[]
    security_event: boolean
    screening_scope: string
    safety: {
      overall: 'PASS' | 'FAIL' | 'UNKNOWN'
      thermal: SafetyCheck
      islanding: SafetyCheck
      snsp: SafetyCheck
      voltage: SafetyCheck
      inertia: SafetyCheck
      rocof: SafetyCheck
      recommendable: boolean
    }
  }
  drivers: string[]
  confidence: {
    forecast: number
    forecast_issue_time: UtcTimestamp
    forecast_source: string
    network_asset_mapping: string
    network_state: 'planning-scenario'
  }
}

export interface SafetyCheck {
  status: 'PASS' | 'FAIL' | 'UNKNOWN'
  reason: string
  evidence: string | null
}

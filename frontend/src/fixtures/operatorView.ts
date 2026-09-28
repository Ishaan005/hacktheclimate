// Representative response for layout work and the smoke test. Nothing here is
// invented: every value is copied from the current reviewed scenario notes.
//
// - Scenario values: docs/NETWORK_SCENARIO_DEMO.md ("Observed screen on the
//   downloaded case") and docs/NETWORK_OUTAGE_RECONCILIATION_2026-09-28.md.
// - Fixed strings: backend/app/network.py, backend/app/network_scenarios.py,
//   scripts/compare_network_scenarios.py, scripts/reconcile_network_outages.py.
//
// This is an EXCERPT: `flows` holds only the monitored branch. The full report
// (all 2,552 flow records) is written to data/raw/network_case/ by the
// scenario script and is untracked. Live mode uses /v1/operator/view instead.
//
// There is no national forecast yet (issue #8), so the forecast is the
// explicit unavailable state rather than sample numbers.

import type { FlowDelta, OperatorView, PlanningScenario, ReviewedOutageOption, ScenarioFlow } from '../types';

const MONITORED = { asset_type: 'branch', asset_id: '1642:5172:1' } as const;
const RATE_A_MVA = 761;

// Flow and loading proxy per run from the documented table. Headroom follows
// the report's formula: rating_mva - abs(flow_mw).
function monitorFlow(flowMw: number, loadingPct: number): ScenarioFlow {
  return {
    ...MONITORED,
    from_bus: 1642,
    to_bus: 5172,
    flow_mw: flowMw,
    rating_mva: RATE_A_MVA,
    dc_loading_pct_proxy: loadingPct,
    dc_headroom_mw_unity_pf_proxy: Math.round((RATE_A_MVA - Math.abs(flowMw)) * 1000) / 1000,
  };
}

const intact = monitorFlow(-153.557, 20.178);
const plannedOutage = monitorFlow(-107.750, 14.159);
const nMinusOne = monitorFlow(-136.898, 17.989);

function monitorDelta(before: ScenarioFlow, after: ScenarioFlow, documentedDelta: number): FlowDelta {
  return {
    ...MONITORED,
    intact_flow_mw: before.flow_mw,
    scenario_flow_mw: after.flow_mw,
    delta_flow_mw: documentedDelta,
    state: 'online',
  };
}

export const fixtureOutages: ReviewedOutageOption[] = [
  {
    outage_id: 'TO-26-CSH-FLA-1-03',
    equipment_description: '220kV FEEDER - CASHLA 220-FLAGFORD 220-1',
  },
];

export const fixtureScenario: PlanningScenario = {
  output_type: 'planning_scenario',
  status: 'ok',
  report: {
    scenario_label: 'planning scenario',
    case_type: 'static TYTFS study case; approximate DC active-power flow',
    case_provenance: {
      source_url: 'https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip',
      source_member: 'TYTFS2024_SV2024_V33.raw',
      source_sha256: 'b73cf0ca51cea4ab8f58cfc4e9e1021f561c877e4880ed979213747b8d667450',
      season: 'summer',
      study_year: 2024,
      scenario_date: '2024-07-01',
      pss_e_version: 33,
      scenario_label: 'TYTFS 2024 planning scenario',
      source_note: 'Reference planning power flow; not a live operational state.',
    },
    rating_basis: 'TYTFS RAW rate A (MVA); active-power comparison is a DC screening proxy',
    outage_reference: 'TO-26-CSH-FLA-1-03; annual programme row 1212; short-term row 73; scheduled/planned evidence only',
    contingency_reference: 'Cashla-Prospect 220 kV circuit 1; adjacent in-service TYTFS branch',
    planned_outage: { asset_type: 'branch', asset_id: '1642:2522:1' },
    contingency: { asset_type: 'branch', asset_id: '1642:4522:1' },
    monitored: MONITORED,
    monitor_by_run: {
      intact,
      planned_outage: plannedOutage,
      selected_n_minus_one: nMinusOne,
    },
    runs: {
      intact: { status: 'ok', reason: null, flows: [intact] },
      planned_outage: { status: 'ok', reason: null, flows: [plannedOutage] },
      selected_n_minus_one: { status: 'ok', reason: null, flows: [nMinusOne] },
    },
    flow_deltas_from_intact: {
      planned_outage: [monitorDelta(intact, plannedOutage, 45.807)],
      // Not stated in the doc: difference of the two documented flows.
      selected_n_minus_one: [monitorDelta(intact, nMinusOne, 16.659)],
    },
    flow_deltas_from_planned_outage: [monitorDelta(plannedOutage, nMinusOne, -29.148)],
    limitations: [
      'Scheduled outage dates do not establish actual equipment state.',
      'DC flow omits voltage, reactive power, losses and dynamic behavior.',
      'MVA rating compared with active MW flow is a screening proxy, not measured thermal headroom.',
      'This is not an EirGrid N-1 security verdict or an actual future line-loading forecast.',
    ],
    outage_review: {
      sources: {
        annual: {
          url: 'https://cms.eirgrid.ie/sites/default/files/publications/2026-Transmission-Outage-Programme-20260907.xlsx',
          http_last_modified: '2026-09-07T13:15:28Z',
        },
        short_term: {
          url: 'https://cms.eirgrid.ie/sites/default/files/publications/Transmission-Outage-Summary-2026-Week-40-41.xlsx',
          http_last_modified: '2026-09-17T14:16:45Z',
        },
      },
      annual: {
        outage_id: 'TO-26-CSH-FLA-1-03',
        equipment_description: '220kV FEEDER - CASHLA 220-FLAGFORD 220-1',
        status: 'Scheduled',
        start_date: '2026-09-24',
        finish_date: '2026-10-02',
        source_row: 1212,
      },
      short_term: {
        outage_id: 'TO-26-CSH-FLA-1-03',
        plant: 'CASHLA FLAGFORD',
        status: 'listed in short-term outage summary; actual state unconfirmed',
        source_row: 73,
      },
      network_match: {
        decision: 'reviewed_scenario_candidate',
        confidence: 'high: unique exact terminals, voltages and circuit; manually reviewed',
        state_warning: 'Scenario operation only; neither publication confirms out-of-service state',
      },
    },
  },
};

export const fixtureOperatorView: OperatorView = {
  forecast: {
    output_type: 'forecast',
    status: 'unavailable',
    reason: 'The national 1–24 hour constraint forecast has not been built yet (issue #8).',
  },
  scenario: null,
};

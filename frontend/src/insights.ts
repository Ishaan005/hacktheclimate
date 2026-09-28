import type { FlowDelta, NationalForecast, RunName, ScenarioFlow, ScenarioReport } from './types';

// Derived, display-only figures. Every value comes from the API response;
// nothing here adds data.

export type Severity = 'normal' | 'caution' | 'critical' | 'unknown';

// Display bands, not EirGrid limits (see GLOSSARY.loadingBand).
export function loadingSeverity(loadingPct: number | null): Severity {
  if (loadingPct === null) return 'unknown';
  if (loadingPct > 100) return 'critical';
  if (loadingPct >= 80) return 'caution';
  return 'normal';
}

export const SEVERITY_TEXT: Record<Severity, string> = {
  normal: 'Within rating',
  caution: 'Near rating',
  critical: 'Over rating',
  unknown: 'No rating',
};

export const RUN_ORDER: RunName[] = ['intact', 'planned_outage', 'selected_n_minus_one'];

export const RUN_LABELS: Record<RunName, string> = {
  intact: 'All equipment in service',
  planned_outage: 'Planned outage',
  selected_n_minus_one: 'Planned outage + selected N-1',
};

export function signedFlowDelta(deltas: FlowDelta[] | null, report: ScenarioReport): number | null {
  const match = deltas?.find(
    (item) => item.asset_type === report.monitored.asset_type && item.asset_id === report.monitored.asset_id,
  );
  return match?.delta_flow_mw ?? null;
}

function flowSize(flow: ScenarioFlow | null): number | null {
  return flow ? Math.abs(flow.flow_mw) : null;
}

export type RunView = {
  name: RunName;
  label: string;
  status: ScenarioReport['runs'][RunName]['status'];
  reason: string | null;
  flowSize: number | null;
  signedFlow: number | null;
  sizeChange: number | null;
  loadingPct: number | null;
  loadingChange: number | null;
  headroom: number | null;
  headroomChange: number | null;
  severity: Severity;
};

// Changes are against the intact run, so each row reads on its own.
export function runViews(report: ScenarioReport): RunView[] {
  const base = report.monitor_by_run.intact;
  return RUN_ORDER.map((name) => {
    const flow = report.monitor_by_run[name];
    const run = report.runs[name];
    const diff = (a: number | null | undefined, b: number | null | undefined) =>
      name === 'intact' || a == null || b == null ? null : a - b;
    return {
      name,
      label: RUN_LABELS[name],
      status: run.status,
      reason: run.reason,
      flowSize: flowSize(flow),
      signedFlow: flow?.flow_mw ?? null,
      sizeChange: diff(flowSize(flow), flowSize(base)),
      loadingPct: flow?.dc_loading_pct_proxy ?? null,
      loadingChange: diff(flow?.dc_loading_pct_proxy, base?.dc_loading_pct_proxy),
      headroom: flow?.dc_headroom_mw_unity_pf_proxy ?? null,
      headroomChange: diff(flow?.dc_headroom_mw_unity_pf_proxy, base?.dc_headroom_mw_unity_pf_proxy),
      severity: loadingSeverity(flow?.dc_loading_pct_proxy ?? null),
    };
  });
}

export function worstRun(views: RunView[]): RunView | null {
  const rated = views.filter((view) => view.loadingPct !== null);
  if (rated.length === 0) return null;
  return rated.reduce((worst, view) => ((view.loadingPct ?? 0) > (worst.loadingPct ?? 0) ? view : worst));
}

// Peak half-hour by expected MWh, for the summary strip.
export function forecastPeak(forecast: NationalForecast) {
  const known = forecast.intervals.filter((item) => item.expected_constraint_mwh !== null);
  if (known.length === 0) return null;
  return known.reduce((peak, item) =>
    (item.expected_constraint_mwh ?? 0) > (peak.expected_constraint_mwh ?? 0) ? item : peak,
  );
}

export function signed(value: number | null, unit: string, digits = 1): string {
  if (value === null) return '';
  const rounded = Number(value.toFixed(digits));
  if (rounded === 0) return `no change`;
  return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded).toFixed(digits)} ${unit}`;
}

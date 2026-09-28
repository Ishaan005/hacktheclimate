import type { ReactNode } from 'react';
import type { OperatorView, ReviewedOutageOption } from '../types';
import { GLOSSARY, STATE_COPY } from '../copy';
import { formatNumber, formatTime } from '../format';
import { forecastPeak, runViews, SEVERITY_TEXT, worstRun } from '../insights';
import Term from './Term';
import './SummaryStrip.css';

type SummaryStripProps = {
  view: OperatorView | null;
  loading: boolean;
  selectedOutage: ReviewedOutageOption | null;
};

type Tile = {
  label: ReactNode;
  value: string;
  detail: string;
  tone: 'normal' | 'caution' | 'critical' | 'unknown';
};

// The current operational picture in three lines, derived only from the
// loaded response.
function SummaryStrip({ view, loading, selectedOutage }: SummaryStripProps) {
  const forecast = view?.forecast;
  const scenario = view?.scenario;
  const decision = view?.decision;

  let riskTile: Tile;
  if (loading && !view) {
    riskTile = { label: 'National constraint risk', value: 'Loading…', detail: '', tone: 'unknown' };
  } else if (!forecast || forecast.status === 'unavailable') {
    riskTile = {
      label: <Term definition={GLOSSARY.constraint}>National constraint risk</Term>,
      value: 'No forecast yet',
      detail: 'Timing of national risk is not shown.',
      tone: 'caution',
    };
  } else {
    const peak = forecastPeak(forecast);
    riskTile = peak
      ? {
          label: <Term definition={GLOSSARY.constraint}>National constraint risk</Term>,
          value: `Highest around ${formatTime(peak.target_timestamp)} UTC`,
          detail: `${formatNumber(peak.expected_constraint_mwh, 'MWh')} expected · ${
            peak.event_probability === null ? 'chance not available' : `${Math.round(peak.event_probability * 100)}% event chance`
          }`,
          tone: 'normal',
        }
      : { label: 'National constraint risk', value: 'No values', detail: 'Every interval is missing.', tone: 'caution' };
  }

  const outageTile: Tile = decision
    ? {
        label: <Term definition={GLOSSARY.plannedOutage}>Outage being studied</Term>,
        value: decision.network.planned_outage.asset_id,
        detail: `TYTFS planning case ${decision.network.case_scenario_date ?? 'date unknown'}`,
        tone: 'unknown',
      }
    : selectedOutage
    ? {
        label: <Term definition={GLOSSARY.plannedOutage}>Outage being studied</Term>,
        value: selectedOutage.equipment_description,
        detail: selectedOutage.outage_id,
        tone: 'unknown',
      }
    : { label: 'Outage being studied', value: 'None selected', detail: 'Choose one in the planning scenario.', tone: 'unknown' };

  let branchTile: Tile = {
    label: 'Monitored branch (planning model)',
    value: '—',
    detail: scenario?.status === 'unavailable' ? 'Outage could not be modelled.' : 'Select an outage to see its effect.',
    tone: 'unknown',
  };
  if (scenario?.status === 'ok') {
    const worst = worstRun(runViews(scenario.report));
    if (worst) {
      branchTile = {
        label: <Term definition={GLOSSARY.loading}>Monitored branch (planning model)</Term>,
        value: `Peak ${worst.loadingPct?.toFixed(1)}% of rate A`,
        detail: `${SEVERITY_TEXT[worst.severity]} · ${worst.label.toLowerCase()}`,
        tone: worst.severity,
      };
    }
  }
  if (decision) {
    const peak = decision.rows.reduce((best, row) =>
      (row.network.max_dc_loading_proxy_pct ?? -1) > (best.network.max_dc_loading_proxy_pct ?? -1) ? row : best,
    );
    branchTile = {
      label: <Term definition={GLOSSARY.loading}>Highest modelled loading (planning case)</Term>,
      value: peak.network.max_dc_loading_proxy_pct === null
        ? 'Unknown' : `${peak.network.max_dc_loading_proxy_pct.toFixed(1)}% of rate A`,
      detail: `Safety ${peak.network.safety.overall} · ${peak.network.worst_asset ?? 'asset unavailable'}`,
      tone: peak.network.safety.overall === 'FAIL' ? 'critical' : 'unknown',
    };
  }

  return (
    <section className="summary-strip" aria-label={decision ? 'Forecast and planning screen' : 'Current picture'}>
      <div className="summary-tiles">
        {[riskTile, outageTile, branchTile].map((tile, index) => (
          <div key={index} className={`summary-tile tone-${tile.tone}`}>
            <p className="tile-label">{tile.label}</p>
            <p className="tile-value">{tile.value}</p>
            {tile.detail && <p className="tile-detail">{tile.detail}</p>}
          </div>
        ))}
      </div>
      <p className="summary-note">{decision ? 'The national forecast supplies timing; the network figures screen a 2024 planning case. No safe action is recommended while required checks are unknown.' : STATE_COPY.independence}</p>
    </section>
  );
}

export default SummaryStrip;

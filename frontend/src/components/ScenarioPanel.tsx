import type { PlanningScenario, ReviewedOutageOption, ScenarioReport, Unavailable } from '../types';
import { COPY, GLOSSARY, STATE_COPY } from '../copy';
import { formatDateTime, formatNumber } from '../format';
import { runViews, SEVERITY_TEXT, worstRun } from '../insights';
import Panel from './Panel';
import SummaryList from './SummaryList';
import StatusMessage from './StatusMessage';
import OutagePicker from './OutagePicker';
import MonitorRunsTable from './MonitorRunsTable';
import DataSourceList from './DataSourceList';
import Term from './Term';
import { AssetMatchBadge } from './ConfidenceBadge';
import './ScenarioPanel.css';

type ScenarioPanelProps = {
  outages: ReviewedOutageOption[];
  selectedOutageId: string | null;
  onSelectOutage: (outageId: string | null) => void;
  scenario: PlanningScenario | Unavailable<'planning_scenario'> | null;
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
};

const SEVERITY_PHRASE = {
  normal: 'well within its rating in this model',
  caution: 'close to its rating in this model',
  critical: 'above its rating in this model',
  unknown: 'with no usable rating in this model',
} as const;

// Plain-language reading of the runs table, built only from report values.
function Finding({ report }: { report: ScenarioReport }) {
  const views = runViews(report);
  const [intact, outage, nMinusOne] = views;
  const worst = worstRun(views);
  const equipment = report.outage_review.annual.equipment_description;
  const unsolved = views.filter((view) => view.status !== 'ok');

  let outageSentence = null;
  if (outage.sizeChange !== null && intact.flowSize !== null && outage.flowSize !== null) {
    const size = Math.abs(outage.sizeChange);
    outageSentence =
      size < 0.05
        ? `Switching off ${equipment} barely changes flow on the monitored branch.`
        : `Switching off ${equipment} ${outage.sizeChange < 0 ? 'reduces' : 'increases'} flow on the monitored branch by ${size.toFixed(1)} MW (from ${intact.flowSize.toFixed(1)} to ${outage.flowSize.toFixed(1)} MW).`;
  }
  return (
    <div className="finding">
      <h3>What the planning model shows</h3>
      <ul>
        {outageSentence && <li>{outageSentence}</li>}
        {nMinusOne.flowSize !== null && (
          <li>
            With the <Term definition={GLOSSARY.nMinusOne}>selected N-1</Term> as well, flow is{' '}
            {nMinusOne.flowSize.toFixed(1)} MW.
          </li>
        )}
        {worst && (
          <li>
            Highest modelled loading is {worst.loadingPct?.toFixed(1)}% of rate A ({worst.label.toLowerCase()}),{' '}
            {SEVERITY_PHRASE[worst.severity]}.
          </li>
        )}
        {unsolved.length > 0 && <li>{unsolved.length} run(s) did not solve cleanly; see the table.</li>}
      </ul>
    </div>
  );
}

function Evidence({ report }: { report: ScenarioReport }) {
  const { case_provenance: provenance, outage_review: review } = report;
  const sources = [
    {
      source: provenance.scenario_label,
      vintage: `${provenance.season} ${provenance.study_year} case, ${provenance.scenario_date}, PSS/E V${provenance.pss_e_version}`,
      retrieved_at: null,
      note: provenance.source_note,
    },
    {
      source: 'Transmission Outage Programme (annual)',
      vintage: `File modified ${formatDateTime(review.sources.annual.http_last_modified)}`,
      retrieved_at: null,
      note: null,
    },
    {
      source: 'Transmission Outage Summary (short term)',
      vintage: `File modified ${formatDateTime(review.sources.short_term.http_last_modified)}`,
      retrieved_at: null,
      note: 'HTTP Last-Modified is a file timestamp, not verified first availability.',
    },
  ];
  const rating = report.monitor_by_run.intact?.rating_mva ?? null;
  return (
    <details className="disclosure">
      <summary>Outage record, planning case, sources and limitations</summary>
      <div className="disclosure-body">
        <div className="block">
          <h3>Outage record</h3>
          <SummaryList
            rows={[
              { key: 'Outage ID', value: <code>{review.annual.outage_id}</code> },
              { key: 'Equipment', value: review.annual.equipment_description },
              { key: 'Programme status', value: review.annual.status },
              {
                key: 'Scheduled window',
                value: `${review.annual.start_date ?? COPY.notAvailable} to ${review.annual.finish_date ?? COPY.notAvailable}`,
              },
              { key: 'Evidence', value: report.outage_reference },
            ]}
          />
        </div>
        <div className="block">
          <h3>Planning case</h3>
          <SummaryList
            rows={[
              { key: 'Outage asset', value: <code>{report.planned_outage.asset_id}</code>, hint: report.planned_outage.asset_type },
              { key: 'Selected N-1', value: <code>{report.contingency.asset_id}</code>, hint: report.contingency_reference },
              { key: 'Affected corridor', value: report.affected_corridor ?? COPY.notAvailable },
              {
                key: 'Rating basis',
                value: rating !== null ? `Rate A ${formatNumber(rating, 'MVA')}` : COPY.notAvailable,
                hint: report.rating_basis,
              },
            ]}
          />
        </div>
        <DataSourceList sources={sources} />
        <div className="block">
          <h3>Model limitations</h3>
          <ul className="limitations">
            {report.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}

function ScenarioControls({ outages, selectedOutageId, onSelectOutage, scenario }: Pick<ScenarioPanelProps, 'outages' | 'selectedOutageId' | 'onSelectOutage' | 'scenario'>) {
  const report = scenario?.status === 'ok' ? scenario.report : null;
  const worst = report ? worstRun(runViews(report)) : null;
  return (
    <div className="scenario-controls">
      <OutagePicker outages={outages} selectedId={selectedOutageId} onSelect={onSelectOutage} />
      {report && (
        <p className="controls-status">
          <Term definition={GLOSSARY.plannedOutage}>{report.outage_review.annual.status}</Term>{' '}
          {report.outage_review.annual.start_date ?? '?'} to {report.outage_review.annual.finish_date ?? '?'}
          {worst && (
            <>
              {' '}
              · peak loading {worst.loadingPct?.toFixed(1)}%{' '}
              <span className={`tag tag-${worst.severity}`}>{SEVERITY_TEXT[worst.severity]}</span>
            </>
          )}
        </p>
      )}
    </div>
  );
}

function ScenarioPanel({ outages, selectedOutageId, onSelectOutage, scenario, loading, error, onRetry }: ScenarioPanelProps) {
  let body;
  if (loading) {
    body = <StatusMessage tone="loading" title={COPY.scenarioLoading} consequence={STATE_COPY.scenarioLoadingConsequence} />;
  } else if (error) {
    body = (
      <StatusMessage
        tone="error"
        title={STATE_COPY.scenarioErrorTitle}
        consequence={STATE_COPY.scenarioErrorConsequence}
        detail={error}
        onRetry={onRetry}
      />
    );
  } else if (!scenario) {
    body = <StatusMessage tone="empty" title={STATE_COPY.scenarioEmptyTitle} consequence={STATE_COPY.scenarioEmptyConsequence} />;
  } else if (scenario.status === 'unavailable') {
    body = (
      <StatusMessage
        tone="unavailable"
        title={STATE_COPY.scenarioUnavailableTitle}
        consequence={STATE_COPY.scenarioUnavailableConsequence}
        detail={scenario.reason}
      />
    );
  } else {
    body = (
      <>
        <Finding report={scenario.report} />
        <MonitorRunsTable report={scenario.report} />
        <AssetMatchBadge match={scenario.report.outage_review.network_match} />
        <Evidence report={scenario.report} />
      </>
    );
  }
  return (
    <Panel kind={COPY.scenarioKind} variant="scenario" title={COPY.scenarioTitle} scope={COPY.scenarioScope} caveat={COPY.scenarioCaveat}>
      <ScenarioControls
        outages={outages}
        selectedOutageId={selectedOutageId}
        onSelectOutage={onSelectOutage}
        scenario={loading || error ? null : scenario}
      />
      {body}
    </Panel>
  );
}

export default ScenarioPanel;

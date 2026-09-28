import type { PlanningScenario, ReviewedOutageOption, ScenarioReport, Unavailable } from '../types';
import { COPY } from '../copy';
import { formatDateTime, formatNumber } from '../format';
import Panel from './Panel';
import SummaryList from './SummaryList';
import StatusMessage from './StatusMessage';
import OutagePicker from './OutagePicker';
import MonitorRunsTable from './MonitorRunsTable';
import DataSourceList from './DataSourceList';
import { AssetMatchBadge } from './ConfidenceBadge';

type ScenarioPanelProps = {
  outages: ReviewedOutageOption[];
  selectedOutageId: string | null;
  onSelectOutage: (outageId: string | null) => void;
  scenario: PlanningScenario | Unavailable<'planning_scenario'> | null;
  loading: boolean;
  error: string | null;
};

function ScenarioBody({ report }: { report: ScenarioReport }) {
  const { case_provenance: provenance, outage_review: review } = report;
  const rating = report.monitor_by_run.intact?.rating_mva ?? null;
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
  return (
    <>
      <MonitorRunsTable report={report} />
      <div className="block">
        <h3>Planned outage</h3>
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
      <AssetMatchBadge match={review.network_match} />
      <DataSourceList sources={sources} />
      <div className="block limitations-block">
        <h3>Model limitations</h3>
        <ul className="limitations">
          {report.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </>
  );
}

function ScenarioPanel({ outages, selectedOutageId, onSelectOutage, scenario, loading, error }: ScenarioPanelProps) {
  let body;
  if (loading) {
    body = <StatusMessage tone="loading" message={COPY.scenarioLoading} />;
  } else if (error) {
    body = <StatusMessage tone="error" message={COPY.scenarioError} detail={error} />;
  } else if (!scenario) {
    body = <StatusMessage tone="empty" message={COPY.scenarioEmpty} />;
  } else if (scenario.status === 'unavailable') {
    body = <StatusMessage tone="unavailable" message={COPY.notAvailable} detail={scenario.reason} />;
  } else {
    body = <ScenarioBody report={scenario.report} />;
  }
  return (
    <Panel kind={COPY.scenarioKind} variant="scenario" title={COPY.scenarioTitle} scope={COPY.scenarioScope} caveat={COPY.scenarioCaveat}>
      <OutagePicker outages={outages} selectedId={selectedOutageId} onSelect={onSelectOutage} />
      {body}
    </Panel>
  );
}

export default ScenarioPanel;

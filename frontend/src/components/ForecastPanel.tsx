import type { NationalForecast, Unavailable } from '../types';
import { COPY } from '../copy';
import { formatDateTime } from '../format';
import Panel from './Panel';
import SummaryList from './SummaryList';
import StatusMessage from './StatusMessage';
import ForecastTimeline from './ForecastTimeline';
import DecisionContextTable from './DecisionContextTable';
import DataSourceList from './DataSourceList';
import { ForecastConfidenceBadge } from './ConfidenceBadge';

type ForecastPanelProps = {
  forecast: NationalForecast | Unavailable<'forecast'> | null;
  loading: boolean;
  error: string | null;
};

function ForecastPanel({ forecast, loading, error }: ForecastPanelProps) {
  let body;
  if (loading) {
    body = <StatusMessage tone="loading" message={COPY.forecastLoading} />;
  } else if (error) {
    body = <StatusMessage tone="error" message={COPY.forecastError} detail={error} />;
  } else if (!forecast || forecast.status === 'unavailable') {
    body = <StatusMessage tone="unavailable" message={COPY.notAvailable} detail={forecast?.reason} />;
  } else {
    body = (
      <>
        <SummaryList
          rows={[
            { key: 'Issued', value: formatDateTime(forecast.issued_at) },
            { key: 'Model', value: <code>{forecast.model_version}</code> },
            { key: 'Event definition', value: forecast.event_definition },
          ]}
        />
        <ForecastConfidenceBadge evaluation={forecast.evaluation} />
        <ForecastTimeline intervals={forecast.intervals} />
        <DecisionContextTable issuedAt={forecast.issued_at} context={forecast.decision_context} />
        <DataSourceList sources={forecast.sources} />
      </>
    );
  }
  return (
    <Panel kind={COPY.forecastKind} variant="forecast" title={COPY.forecastTitle} scope={COPY.forecastScope} caveat={COPY.forecastCaveat}>
      {body}
    </Panel>
  );
}

export default ForecastPanel;

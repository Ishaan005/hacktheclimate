import type { NationalForecast, Unavailable } from '../types';
import './ForecastPanel.css';
import { COPY, GLOSSARY, STATE_COPY } from '../copy';
import { formatDateTime } from '../format';
import Panel from './Panel';
import SummaryList from './SummaryList';
import StatusMessage from './StatusMessage';
import ForecastTimeline from './ForecastTimeline';
import DecisionContextTable from './DecisionContextTable';
import DataSourceList from './DataSourceList';
import Term from './Term';
import { ForecastConfidenceBadge } from './ConfidenceBadge';

type ForecastPanelProps = {
  forecast: NationalForecast | Unavailable<'forecast'> | null;
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
};

function ForecastBody({ forecast }: { forecast: NationalForecast }) {
  const stale = forecast.sources.filter((item) => item.status === 'stale' || item.status === 'unavailable');
  return (
    <>
      {stale.length > 0 && (
        <StatusMessage
          tone="stale"
          title={STATE_COPY.forecastStaleTitle}
          consequence={`${STATE_COPY.forecastStaleConsequence} ${stale.map((item) => item.source).join(', ')}.`}
        />
      )}
      <ForecastTimeline intervals={forecast.intervals} />
      <ForecastConfidenceBadge evaluation={forecast.evaluation} />
      <div className="block">
        <h3>About this forecast</h3>
        <SummaryList
          rows={[
            { key: 'Issued', value: formatDateTime(forecast.issued_at) },
            {
              key: 'Event',
              value: <Term definition={GLOSSARY.eventProbability}>{forecast.event_definition}</Term>,
            },
            { key: 'Model version', value: <code>{forecast.model_version}</code> },
          ]}
        />
      </div>
      <details className="disclosure">
        <summary>Inputs and sources</summary>
        <DecisionContextTable issuedAt={forecast.issued_at} context={forecast.decision_context} />
        <DataSourceList sources={forecast.sources} />
      </details>
    </>
  );
}

function ForecastPanel({ forecast, loading, error, onRetry }: ForecastPanelProps) {
  let body;
  if (loading) {
    body = <StatusMessage tone="loading" title={COPY.forecastLoading} consequence={STATE_COPY.forecastLoadingConsequence} />;
  } else if (error) {
    body = (
      <StatusMessage
        tone="error"
        title={STATE_COPY.forecastErrorTitle}
        consequence={STATE_COPY.forecastErrorConsequence}
        detail={error}
        onRetry={onRetry}
      />
    );
  } else if (!forecast || forecast.status === 'unavailable') {
    body = (
      <StatusMessage
        tone="unavailable"
        title={STATE_COPY.forecastUnavailableTitle}
        consequence={STATE_COPY.forecastUnavailableConsequence}
        detail={forecast?.reason}
      />
    );
  } else {
    body = <ForecastBody forecast={forecast} />;
  }
  return (
    <Panel kind={COPY.forecastKind} variant="forecast" title={COPY.forecastTitle} scope={COPY.forecastScope} caveat={COPY.forecastCaveat}>
      {body}
    </Panel>
  );
}

export default ForecastPanel;

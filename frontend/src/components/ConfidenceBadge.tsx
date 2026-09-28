import type { ForecastEvaluation, OutageReview } from '../types';
import { COPY } from '../copy';
import SummaryList from './SummaryList';

// Forecast confidence and asset-match confidence answer different questions,
// so they are separate blocks with their own headings.

const CALIBRATION_TEXT: Record<ForecastEvaluation['calibration_status'], string> = {
  calibrated: 'Calibrated',
  uncalibrated: 'Not calibrated',
  unknown: 'Calibration unknown',
};

function fraction(value: number | null): string {
  return value === null ? COPY.notAvailable : `${Math.round(value * 100)}%`;
}

export function ForecastConfidenceBadge({ evaluation }: { evaluation: ForecastEvaluation }) {
  const baselineText =
    evaluation.beats_baseline === null
      ? 'Baseline comparison not available'
      : `${evaluation.beats_baseline ? 'Beats' : 'Does not beat'} ${evaluation.baseline ?? 'baseline'}`;
  return (
    <div className="block">
      <h3>
        {COPY.forecastConfidence}{' '}
        <span className={`tag tag-${evaluation.calibration_status}`}>{CALIBRATION_TEXT[evaluation.calibration_status]}</span>
      </h3>
      <SummaryList
        rows={[
          { key: 'Test period', value: evaluation.test_period ?? COPY.notAvailable, hint: 'Chronological backtest' },
          { key: 'Event prevalence', value: fraction(evaluation.event_prevalence) },
          { key: 'PR-AUC', value: evaluation.pr_auc === null ? COPY.notAvailable : evaluation.pr_auc.toFixed(2) },
          {
            key: 'Interval coverage',
            value: `${fraction(evaluation.interval_coverage)} (target ${fraction(evaluation.interval_nominal)})`,
          },
          { key: 'Against baseline', value: baselineText, hint: evaluation.note ?? undefined },
        ]}
      />
    </div>
  );
}

const DECISION_TEXT: Record<OutageReview['network_match']['decision'], string> = {
  reviewed_scenario_candidate: 'Reviewed match',
  candidate_requires_manual_review: 'Needs manual review',
  unresolved: 'Not matched',
};

export function AssetMatchBadge({ match }: { match: OutageReview['network_match'] }) {
  return (
    <div className="block">
      <h3>
        {COPY.assetMatchConfidence}{' '}
        <span className={`tag tag-${match.decision}`}>{DECISION_TEXT[match.decision]}</span>
      </h3>
      <SummaryList
        rows={[
          ...(match.confidence ? [{ key: 'Confidence', value: match.confidence }] : []),
          ...(match.reason ? [{ key: 'Reason', value: match.reason }] : []),
          ...(match.state_warning ? [{ key: 'Equipment state', value: match.state_warning }] : []),
        ]}
      />
    </div>
  );
}

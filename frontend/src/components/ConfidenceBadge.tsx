import type { ForecastEvaluation, OutageReview } from '../types';
import { COPY, GLOSSARY } from '../copy';
import SummaryList from './SummaryList';
import Term from './Term';

// Forecast confidence and asset-match confidence answer different questions,
// so they are separate blocks with their own headings and definitions.

const CALIBRATION: Record<ForecastEvaluation['calibration_status'], { text: string; tone: string }> = {
  calibrated: { text: 'Calibrated', tone: 'normal' },
  uncalibrated: { text: 'Not calibrated', tone: 'caution' },
  unknown: { text: 'Calibration unknown', tone: 'caution' },
};

function fraction(value: number | null): string {
  return value === null ? COPY.notAvailable : `${Math.round(value * 100)}%`;
}

function baselineSentence(evaluation: ForecastEvaluation): string {
  if (evaluation.beats_baseline === null) return 'Baseline comparison not available';
  const baseline = evaluation.baseline ?? 'the simple baseline';
  return evaluation.beats_baseline
    ? `Did better than ${baseline} on past data`
    : `Did not beat ${baseline} on past data: treat with extra caution`;
}

export function ForecastConfidenceBadge({ evaluation }: { evaluation: ForecastEvaluation }) {
  const calibration = CALIBRATION[evaluation.calibration_status];
  return (
    <div className="block">
      <h3>
        <Term definition={GLOSSARY.confidence}>{COPY.forecastConfidence}</Term>{' '}
        <span className={`tag tag-${calibration.tone}`}>{calibration.text}</span>
      </h3>
      <p className="lead">{baselineSentence(evaluation)}</p>
      <SummaryList
        rows={[
          { key: 'Tested on', value: evaluation.test_period ?? COPY.notAvailable },
          {
            key: 'Ranking score',
            value: (
              <>
                <Term definition={GLOSSARY.prAuc}>PR-AUC</Term>{' '}
                {evaluation.pr_auc === null ? COPY.notAvailable : evaluation.pr_auc.toFixed(2)}
              </>
            ),
            hint: `Events in ${fraction(evaluation.event_prevalence)} of test half-hours`,
          },
          {
            key: 'Range reliability',
            value: (
              <Term definition={GLOSSARY.intervalCoverage}>
                {`${fraction(evaluation.interval_coverage)} inside range (target ${fraction(evaluation.interval_nominal)})`}
              </Term>
            ),
          },
        ]}
      />
      {evaluation.note && <p className="block-hint">{evaluation.note}</p>}
    </div>
  );
}

const DECISION: Record<OutageReview['network_match']['decision'], { text: string; tone: string }> = {
  reviewed_scenario_candidate: { text: 'Reviewed match', tone: 'normal' },
  candidate_requires_manual_review: { text: 'Needs manual review', tone: 'caution' },
  unresolved: { text: 'Not matched', tone: 'critical' },
};

export function AssetMatchBadge({ match }: { match: OutageReview['network_match'] }) {
  const decision = DECISION[match.decision];
  return (
    <div className="block">
      <h3>
        <Term definition={GLOSSARY.assetMatch}>{COPY.assetMatchConfidence}</Term>{' '}
        <span className={`tag tag-${decision.tone}`}>{decision.text}</span>
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

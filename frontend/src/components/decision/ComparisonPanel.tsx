import type { ReactNode } from 'react';
import { BENEFIT_COPY, COLUMN_LABEL, COLUMN_ORDER, COMPARISON_COPY } from '../../decision/copy/comparison';
import { NOT_ESTABLISHED, RESULT_LABEL, STALE_NOTE } from '../../decision/copy/shared';
import { canClaimBenefit, outcomeFor, windowMismatches } from '../../decision/rules';
import type { Benefits, ComparisonColumn, Established, OutcomeState, SafetyResult, ViewMode } from '../../decision/types';
import { formatDayTime, formatEur, formatTime } from '../../format';
import { ResultChip } from './ResultChip';
import './ComparisonPanel.css';

const BASELINE: ComparisonColumn = 'no_new_instruction';

// Bare number in the Established unit. Negative values use a true minus.
function formatBare(value: number, unit: string): string {
  if (unit === 'EUR') return formatEur(value);
  const digits = Number.isInteger(value) ? 0 : 1;
  return `${value < 0 ? '−' : ''}${Math.abs(value).toFixed(digits)}`;
}

function formatWithUnit(value: number, unit: string): string {
  const bare = formatBare(value, unit);
  if (unit === 'EUR') return bare;
  return unit === '%' ? `${bare}%` : `${bare} ${unit}`;
}

function hasValue(value: Established): value is Established & { value: number } {
  return value.value !== null && Number.isFinite(value.value);
}

// Value, range and method; or Not established with the reason. Null is
// never shown as zero.
function EstablishedValue({ value, requireRange = false }: { value: Established; requireRange?: boolean }) {
  if (!hasValue(value)) {
    return (
      <>
        <span className="established-value established-missing">{NOT_ESTABLISHED}</span>
        <span className="established-note">{value.notEstablishedReason ?? COMPARISON_COPY.noReason}</span>
      </>
    );
  }
  const range = value.lower !== null && value.upper !== null
    ? `(${formatBare(value.lower, value.unit)}–${formatBare(value.upper, value.unit)})`
    : null;
  const basis = [value.method, value.source].filter(Boolean).join(' · ');
  return (
    <>
      <span className="established-value">
        {formatWithUnit(value.value, value.unit)}
        {range && <span className="established-range"> {range}</span>}
      </span>
      {!range && requireRange && <span className="established-note">{COMPARISON_COPY.range}: {NOT_ESTABLISHED.toLowerCase()}</span>}
      {basis && <span className="established-note">{basis}</span>}
    </>
  );
}

type CardEntry = { name?: string; value: Established };

type CardProps = {
  label: string;
  entries: CardEntry[];
  details?: string[];
  // Set when the proposed plan's safety is not a pass: numbers stay visible,
  // greyed, as context only.
  blockedBy: SafetyResult | null;
  requireRange?: boolean;
  children?: ReactNode;
};

export function EstablishedCard({ label, entries, details = [], blockedBy, requireRange, children }: CardProps) {
  return (
    <div className={`metric established-card${blockedBy ? ' established-card-blocked' : ''}`}>
      <dt className="metric-label established-card-label">{label}</dt>
      {blockedBy && (
        <dd className="established-card-claim">
          {BENEFIT_COPY.cannotClaim(RESULT_LABEL[blockedBy])}
          <span className="established-note">{BENEFIT_COPY.contextOnly}</span>
        </dd>
      )}
      {entries.map((entry, index) => (
        <dd key={entry.name ?? index} className="established-card-entry">
          {entry.name && <span className="established-card-name">{entry.name}</span>}
          <EstablishedValue value={entry.value} requireRange={requireRange} />
        </dd>
      ))}
      {children}
      {details.map((detail) => <dd key={detail} className="metric-detail">{detail}</dd>)}
    </div>
  );
}

type RowSpec = { label: string; render: (outcome: OutcomeState) => ReactNode };

const SAFETY_ROWS: RowSpec[] = [
  { label: COMPARISON_COPY.rows.safety, render: (outcome) => <ResultChip result={outcome.safety} prefix={`${COLUMN_LABEL[outcome.column]} safety result`} /> },
  {
    label: COMPARISON_COPY.rows.worstMargin,
    render: (outcome) => outcome.worstMargin
      ? <span className="established-value">{outcome.worstMargin}</span>
      : <span className="established-value established-missing">{NOT_ESTABLISHED}</span>,
  },
  { label: COMPARISON_COPY.rows.deliveredRelief, render: (outcome) => <EstablishedValue value={outcome.deliveredReliefMw} /> },
  { label: COMPARISON_COPY.rows.responseTime, render: (outcome) => <EstablishedValue value={outcome.responseTimeMinutes} /> },
  { label: COMPARISON_COPY.rows.timeToBreach, render: (outcome) => <EstablishedValue value={outcome.timeToBreachMinutes} /> },
];

// Constrained and curtailed stay separate rows: they are different causes.
const DISPATCH_DOWN_ROWS: RowSpec[] = [
  { label: COMPARISON_COPY.rows.constrained, render: (outcome) => <EstablishedValue value={outcome.constrainedMwh} /> },
  { label: COMPARISON_COPY.rows.curtailed, render: (outcome) => <EstablishedValue value={outcome.curtailedMwh} /> },
];

function RowGroup({ title, rows, columns }: { title: string; rows: RowSpec[]; columns: (OutcomeState | undefined)[] }) {
  return (
    <tbody>
      <tr className="comparison-group">
        <th scope="colgroup" colSpan={columns.length + 1}>{title}</th>
      </tr>
      {rows.map((row) => (
        <tr key={row.label}>
          <th scope="row">{row.label}</th>
          {columns.map((outcome, index) => (
            <td key={COLUMN_ORDER[index]} className={COLUMN_ORDER[index] === BASELINE ? 'comparison-baseline' : undefined}>
              {outcome?.available
                ? row.render(outcome)
                : <span className="established-value established-missing">{NOT_ESTABLISHED}</span>}
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

type Props = {
  outcomes: OutcomeState[];
  benefits: Benefits;
  view: ViewMode;
  stale: boolean;
};

// Four plan states over one window. Safety rows come first; benefit cards
// follow and cannot be claimed unless the proposed plan passes safety.
function ComparisonPanel({ outcomes, benefits, view, stale }: Props) {
  const columns = COLUMN_ORDER.map((column) => outcomeFor(outcomes, column));
  const reference = columns.find((outcome) => outcome?.available);
  const mismatched = windowMismatches(outcomes);
  const proposed = outcomeFor(outcomes, 'proposed');
  const blockedBy: SafetyResult | null = canClaimBenefit(proposed)
    ? null
    : proposed?.available && proposed.safety === 'fail' ? 'fail' : 'unknown';
  const siteRisk = [benefits.siteRiskProbability, benefits.siteRiskExpectedMwh];
  const siteEstablished = siteRisk.some(hasValue);
  const siteReasons = [...new Set(siteRisk.map((value) => value.notEstablishedReason ?? COMPARISON_COPY.noReason))];

  return (
    <section className="card comparison-panel" aria-labelledby="comparison-heading">
      <h3 id="comparison-heading" className="card-kicker">{COMPARISON_COPY.title}</h3>
      {reference && (
        <p className="comparison-window">
          {COMPARISON_COPY.window(`${formatDayTime(reference.windowStart)}–${formatTime(reference.windowEnd)}`)}
        </p>
      )}
      {mismatched.length > 0 && (
        <p className="comparison-warning" role="alert">
          {COMPARISON_COPY.mismatch(mismatched.map((column) => COLUMN_LABEL[column]).join(', '))}
        </p>
      )}
      {stale && <p className="comparison-stale" role="status">{STALE_NOTE}</p>}

      <div className="table-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">{COMPARISON_COPY.measure}</th>
              {COLUMN_ORDER.map((column, index) => {
                const outcome = columns[index];
                return (
                  <th key={column} scope="col" className={column === BASELINE ? 'comparison-baseline' : undefined}>
                    <span className="comparison-column-name">{COLUMN_LABEL[column]}</span>
                    {column === BASELINE && <span className="comparison-baseline-tag">{COMPARISON_COPY.baselineTag}</span>}
                    {!outcome?.available && (
                      <span className="comparison-unavailable">
                        <span className="established-missing">{NOT_ESTABLISHED}</span>
                        <span className="established-note">{outcome?.unavailableReason ?? COMPARISON_COPY.notEvaluated}</span>
                      </span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <RowGroup title={COMPARISON_COPY.safetyGroup} rows={SAFETY_ROWS} columns={columns} />
          <RowGroup title={COMPARISON_COPY.dispatchDownGroup} rows={DISPATCH_DOWN_ROWS} columns={columns} />
        </table>
      </div>

      <h4 className="comparison-benefits-title">{BENEFIT_COPY.title}</h4>
      {blockedBy && <p className="comparison-warning">{BENEFIT_COPY.cannotClaimNote}</p>}
      <dl className="metrics comparison-benefits">
        <EstablishedCard
          label={BENEFIT_COPY.avoided}
          entries={[{ value: benefits.avoidedDispatchDownMwh }]}
          details={[BENEFIT_COPY.avoidedDetail, BENEFIT_COPY.avoidedNote]}
          blockedBy={blockedBy}
          requireRange
        />
        <EstablishedCard
          label={BENEFIT_COPY.siteRisk}
          entries={siteEstablished ? [
            { name: BENEFIT_COPY.siteProbability, value: benefits.siteRiskProbability },
            { name: BENEFIT_COPY.siteExpected, value: benefits.siteRiskExpectedMwh },
          ] : []}
          details={view === 'national' ? [BENEFIT_COPY.siteNationalView] : []}
          blockedBy={blockedBy}
        >
          {!siteEstablished && (
            <dd className="established-card-entry">
              <span className="established-value established-missing">{NOT_ESTABLISHED}</span>
              <span className="established-note">{siteReasons.join(' ')}</span>
            </dd>
          )}
          {!siteEstablished && benefits.nationalContext && (
            <dd className="established-card-context">
              <span className="established-card-name">{BENEFIT_COPY.nationalContext}</span>
              {benefits.nationalContext}
            </dd>
          )}
        </EstablishedCard>
        <EstablishedCard
          label={BENEFIT_COPY.systemCost}
          entries={[{ value: benefits.netSystemResourceCostEur }]}
          details={[BENEFIT_COPY.perspective(benefits.netSystemResourceCostEur.perspective)]}
          blockedBy={blockedBy}
        />
        <EstablishedCard
          label={BENEFIT_COPY.marketOpportunity}
          entries={[{ value: benefits.grossMarketOpportunityEur }]}
          details={[BENEFIT_COPY.marketNote]}
          blockedBy={blockedBy}
        />
        <EstablishedCard
          label={BENEFIT_COPY.financialValue}
          entries={[{ value: benefits.netFinancialValueEur }]}
          details={[BENEFIT_COPY.perspective(benefits.netFinancialValueEur.perspective), BENEFIT_COPY.financialNote]}
          blockedBy={blockedBy}
        />
        <EstablishedCard
          label={BENEFIT_COPY.carbon}
          entries={[{ value: benefits.carbonEffectTco2e }]}
          details={[BENEFIT_COPY.carbonNote]}
          blockedBy={blockedBy}
          requireRange
        />
      </dl>
    </section>
  );
}

export default ComparisonPanel;

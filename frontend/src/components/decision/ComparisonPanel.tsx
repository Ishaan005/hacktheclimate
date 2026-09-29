import type { ReactNode } from 'react';
import { BENEFIT_COPY, COLUMN_LABEL, COLUMN_ORDER, COMPARISON_COPY } from '../../decision/copy/comparison';
import { NOT_ESTABLISHED, RESULT_LABEL, STALE_NOTE } from '../../decision/copy/shared';
import { canClaimBenefit, outcomeFor, windowMismatches } from '../../decision/rules';
import type { Benefits, ComparisonColumn, Established, OutcomeState, SafetyResult, ViewMode } from '../../decision/types';
import { formatDayTime, formatEur, formatTime, parseUtc } from '../../format';
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
function EstablishedValue({ value }: { value: Established }) {
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
  children?: ReactNode;
};

export function EstablishedCard({ label, entries, details = [], blockedBy, children }: CardProps) {
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
          <EstablishedValue value={entry.value} />
        </dd>
      ))}
      {children}
      {details.map((detail) => <dd key={detail} className="metric-detail">{detail}</dd>)}
    </div>
  );
}

type RowSpec = { label: string; hasData: (outcome: OutcomeState) => boolean; render: (outcome: OutcomeState) => ReactNode };

const SAFETY_ROWS: RowSpec[] = [
  { label: COMPARISON_COPY.rows.safety, hasData: () => true, render: (outcome) => <ResultChip result={outcome.safety} prefix={`${COLUMN_LABEL[outcome.column]} safety result`} /> },
  {
    label: COMPARISON_COPY.rows.worstMargin,
    hasData: (outcome) => outcome.worstMargin !== null,
    render: (outcome) => outcome.worstMargin
      ? <span className="established-value">{outcome.worstMargin}</span>
      : <span className="established-value established-missing">{NOT_ESTABLISHED}</span>,
  },
  { label: COMPARISON_COPY.rows.deliveredRelief, hasData: (outcome) => hasValue(outcome.deliveredReliefMw), render: (outcome) => <EstablishedValue value={outcome.deliveredReliefMw} /> },
  { label: COMPARISON_COPY.rows.responseTime, hasData: (outcome) => hasValue(outcome.responseTimeMinutes), render: (outcome) => <EstablishedValue value={outcome.responseTimeMinutes} /> },
  { label: COMPARISON_COPY.rows.timeToBreach, hasData: (outcome) => hasValue(outcome.timeToBreachMinutes), render: (outcome) => <EstablishedValue value={outcome.timeToBreachMinutes} /> },
];

// Constrained and curtailed stay separate rows: they are different causes.
const DISPATCH_DOWN_ROWS: RowSpec[] = [
  { label: COMPARISON_COPY.rows.constrained, hasData: (outcome) => hasValue(outcome.constrainedMwh), render: (outcome) => <EstablishedValue value={outcome.constrainedMwh} /> },
  { label: COMPARISON_COPY.rows.curtailed, hasData: (outcome) => hasValue(outcome.curtailedMwh), render: (outcome) => <EstablishedValue value={outcome.curtailedMwh} /> },
];

function RowGroup({ title, rows, columns }: { title: string; rows: RowSpec[]; columns: OutcomeState[] }) {
  if (!rows.length) return null;
  return (
    <tbody>
      <tr className="comparison-group">
        <th scope="colgroup" colSpan={columns.length + 1}>{title}</th>
      </tr>
      {rows.map((row) => (
        <tr key={row.label}>
          <th scope="row">{row.label}</th>
          {columns.map((outcome) => (
            <td key={outcome.column} className={outcome.column === BASELINE ? 'comparison-baseline' : undefined}>
              {row.hasData(outcome) ? row.render(outcome) : <span aria-label={NOT_ESTABLISHED}>—</span>}
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
  demo?: boolean;
};

// Four plan states over one window. Safety rows come first; benefit cards
// follow and cannot be claimed unless the proposed plan passes safety.
function ComparisonPanel({ outcomes, benefits, view, stale, demo = false }: Props) {
  const columns = COLUMN_ORDER.map((column) => outcomeFor(outcomes, column)).filter((outcome): outcome is OutcomeState => outcome?.available === true);
  const reference = columns[0];
  const mismatched = windowMismatches(columns);
  const proposed = outcomeFor(outcomes, 'proposed');
  const blockedBy: SafetyResult | null = canClaimBenefit(proposed)
    ? null
    : proposed?.available && proposed.safety === 'fail' ? 'fail' : 'unknown';
  const siteRisk = [benefits.siteRiskProbability, benefits.siteRiskExpectedMwh];
  const siteEstablished = siteRisk.some(hasValue);
  const benefitAvailable = [benefits.avoidedDispatchDownMwh, ...siteRisk, benefits.netSystemResourceCostEur,
    benefits.grossMarketOpportunityEur, benefits.netFinancialValueEur, benefits.carbonEffectTco2e].some(hasValue);
  const safetyRows = SAFETY_ROWS.filter((row) => columns.some(row.hasData));
  const dispatchRows = DISPATCH_DOWN_ROWS.filter((row) => columns.some(row.hasData));
  const windowText = reference && parseUtc(reference.windowStart).toISOString().slice(0, 10) === parseUtc(reference.windowEnd).toISOString().slice(0, 10)
    ? `${formatDayTime(reference.windowStart)}–${formatTime(reference.windowEnd)}`
    : reference ? `${formatDayTime(reference.windowStart)} – ${formatDayTime(reference.windowEnd)}` : null;

  if (!columns.length && !benefitAvailable && (!benefits.nationalContext || demo)) return null;

  return (
    <section className="card comparison-panel" aria-labelledby="comparison-heading">
      <h3 id="comparison-heading" className="card-kicker">{COMPARISON_COPY.title}</h3>
      {windowText && (
        <p className="comparison-window">
          {COMPARISON_COPY.window(windowText)}
        </p>
      )}
      {mismatched.length > 0 && (
        <p className="comparison-warning" role="alert">
          {COMPARISON_COPY.mismatch(mismatched.map((column) => COLUMN_LABEL[column]).join(', '))}
        </p>
      )}
      {stale && <p className="comparison-stale" role="status">{STALE_NOTE}</p>}

      {columns.length > 0 && <div className="table-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">{COMPARISON_COPY.measure}</th>
              {columns.map((outcome) => {
                const column = outcome.column;
                return (
                  <th key={column} scope="col" className={column === BASELINE ? 'comparison-baseline' : undefined}>
                    <span className="comparison-column-name">{COLUMN_LABEL[column]}</span>
                    {column === BASELINE && <span className="comparison-baseline-tag">{COMPARISON_COPY.baselineTag}</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <RowGroup title={COMPARISON_COPY.safetyGroup} rows={safetyRows} columns={columns} />
          <RowGroup title={COMPARISON_COPY.dispatchDownGroup} rows={dispatchRows} columns={columns} />
        </table>
      </div>}

      {(benefitAvailable || (benefits.nationalContext && !demo)) && <>
      <h4 className="comparison-benefits-title">{demo ? 'Modeled outcome context' : BENEFIT_COPY.title}</h4>
      {demo && benefitAvailable && <p className="comparison-warning">
        {blockedBy ? 'Demo estimate only. Safety is not approved for this action.' : 'Demo estimate only; not an operationally validated benefit.'}
      </p>}
      {!demo && blockedBy && benefitAvailable && <p className="comparison-warning">{BENEFIT_COPY.cannotClaimNote}</p>}
      <dl className="metrics comparison-benefits">
        {hasValue(benefits.avoidedDispatchDownMwh) &&
        <EstablishedCard
          label={demo && blockedBy ? 'Modeled dispatch-down difference' : BENEFIT_COPY.avoided}
          entries={[{ value: benefits.avoidedDispatchDownMwh }]}
          details={demo ? [] : [BENEFIT_COPY.avoidedDetail, BENEFIT_COPY.avoidedNote]}
          blockedBy={demo ? null : blockedBy}
        />}
        {siteEstablished && <EstablishedCard
          label={BENEFIT_COPY.siteRisk}
          entries={[
            ...(hasValue(benefits.siteRiskProbability) ? [{ name: BENEFIT_COPY.siteProbability, value: benefits.siteRiskProbability }] : []),
            ...(hasValue(benefits.siteRiskExpectedMwh) ? [{ name: BENEFIT_COPY.siteExpected, value: benefits.siteRiskExpectedMwh }] : []),
          ]}
          details={view === 'national' ? [BENEFIT_COPY.siteNationalView] : []}
          blockedBy={demo ? null : blockedBy}
        />}
        {benefits.nationalContext && !demo && <div className="metric established-card">
          <dt className="metric-label established-card-label">{BENEFIT_COPY.nationalContext}</dt>
          <dd className="established-card-entry">{benefits.nationalContext}</dd>
        </div>}
        {hasValue(benefits.netSystemResourceCostEur) && <EstablishedCard
          label={BENEFIT_COPY.systemCost}
          entries={[{ value: benefits.netSystemResourceCostEur }]}
          details={[BENEFIT_COPY.perspective(benefits.netSystemResourceCostEur.perspective)]}
          blockedBy={demo ? null : blockedBy}
        />}
        {hasValue(benefits.grossMarketOpportunityEur) && <EstablishedCard
          label={BENEFIT_COPY.marketOpportunity}
          entries={[{ value: benefits.grossMarketOpportunityEur }]}
          details={[BENEFIT_COPY.marketNote]}
          blockedBy={demo ? null : blockedBy}
        />}
        {hasValue(benefits.netFinancialValueEur) && <EstablishedCard
          label={BENEFIT_COPY.financialValue}
          entries={[{ value: benefits.netFinancialValueEur }]}
          details={[BENEFIT_COPY.perspective(benefits.netFinancialValueEur.perspective), BENEFIT_COPY.financialNote]}
          blockedBy={demo ? null : blockedBy}
        />}
        {hasValue(benefits.carbonEffectTco2e) && <EstablishedCard
          label={BENEFIT_COPY.carbon}
          entries={[{ value: benefits.carbonEffectTco2e }]}
          details={[BENEFIT_COPY.carbonNote]}
          blockedBy={demo ? null : blockedBy}
        />}
      </dl>
      </>}
    </section>
  );
}

export default ComparisonPanel;

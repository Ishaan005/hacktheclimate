import type { ReactNode } from 'react';
import { BENEFIT_COPY, COLUMN_LABEL, COLUMN_ORDER, COMPARISON_COPY } from '../../decision/copy/comparison';
import { NOT_ESTABLISHED, RESULT_LABEL } from '../../decision/copy/shared';
import { canClaimBenefit, outcomeFor, windowMismatches } from '../../decision/rules';
import type { Benefits, ComparisonColumn, Established, OutcomeState, ViewMode } from '../../decision/types';
import { formatEur, formatWindow } from '../../format';
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

function Missing() {
  return (
    <span className="established-value">
      <span className="established-missing">{NOT_ESTABLISHED}</span>
    </span>
  );
}

// Value with range and basis. Null is never shown as zero.
function ValueWithBasis({ value, requireRange = false }: { value: Established & { value: number }; requireRange?: boolean }) {
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
  // Numbers stay readable but faint: context only, not a claim.
  greyed?: boolean;
  requireRange?: boolean;
  children?: ReactNode;
};

export function EstablishedCard({ label, entries, details = [], greyed = false, requireRange, children }: CardProps) {
  return (
    <div className={`metric established-card${greyed ? ' established-card-greyed' : ''}`}>
      <dt className="metric-label">{label}</dt>
      {entries.map((entry, index) => (
        <dd key={entry.name ?? index} className="established-card-entry">
          {entry.name && <span className="established-card-name">{entry.name}</span>}
          {hasValue(entry.value)
            ? <ValueWithBasis value={entry.value} requireRange={requireRange} />
            : <Missing />}
        </dd>
      ))}
      {children}
      {details.map((detail) => <dd key={detail} className="metric-detail">{detail}</dd>)}
    </div>
  );
}

// A row either reads an Established value or renders its own cell.
type RowSpec = {
  label: string;
  value?: (outcome: OutcomeState) => Established;
  render?: (outcome: OutcomeState) => ReactNode;
};

const SAFETY_ROWS: RowSpec[] = [
  { label: COMPARISON_COPY.rows.safety, render: (outcome) => <ResultChip result={outcome.safety} prefix={`${COLUMN_LABEL[outcome.column]} safety result`} /> },
  {
    label: COMPARISON_COPY.rows.worstMargin,
    render: (outcome) => outcome.worstMargin
      ? <span className="established-value">{outcome.worstMargin}</span>
      : <Missing />,
  },
  { label: COMPARISON_COPY.rows.deliveredRelief, value: (outcome) => outcome.deliveredReliefMw },
  { label: COMPARISON_COPY.rows.responseTime, value: (outcome) => outcome.responseTimeMinutes },
  { label: COMPARISON_COPY.rows.timeToBreach, value: (outcome) => outcome.timeToBreachMinutes },
];

// Constrained and curtailed stay separate rows: they are different causes.
const DISPATCH_DOWN_ROWS: RowSpec[] = [
  { label: COMPARISON_COPY.rows.constrained, value: (outcome) => outcome.constrainedMwh },
  { label: COMPARISON_COPY.rows.curtailed, value: (outcome) => outcome.curtailedMwh },
];

type Columns = (OutcomeState | undefined)[];

type GroupProps = { title: string; rows: RowSpec[]; columns: Columns };

function RowGroup({ title, rows, columns }: GroupProps) {
  return (
    <tbody>
      <tr className="comparison-group">
        <th scope="colgroup" colSpan={columns.length + 1} className="panel-section-title">{title}</th>
      </tr>
      {rows.map((row) => (
        <tr key={row.label}>
          <th scope="row">{row.label}</th>
          {columns.map((outcome, index) => {
            let cell: ReactNode;
            if (!outcome?.available) {
              // No plan in this column: a dash, not a value.
              cell = (
                <>
                  <span className="established-missing comparison-dash" aria-hidden="true">—</span>
                  <span className="visually-hidden">{NOT_ESTABLISHED}</span>
                </>
              );
            } else if (row.value) {
              const value = row.value(outcome);
              cell = hasValue(value) ? <ValueWithBasis value={value} /> : <Missing />;
            } else {
              cell = row.render?.(outcome);
            }
            return (
              <td key={COLUMN_ORDER[index]} className={COLUMN_ORDER[index] === BASELINE ? 'comparison-baseline' : undefined}>
                {cell}
              </td>
            );
          })}
        </tr>
      ))}
    </tbody>
  );
}

type Props = {
  outcomes: OutcomeState[];
  benefits: Benefits;
  view: ViewMode;
  demo?: boolean;
};

// Four plan states over one window. Safety rows come first; benefits
// follow and cannot be claimed unless the proposed plan passes safety.
function ComparisonPanel({ outcomes, benefits, view, demo = false }: Props) {
  const columns = COLUMN_ORDER.map((column) => outcomeFor(outcomes, column));
  const reference = columns.find((outcome) => outcome?.available);
  const mismatched = windowMismatches(outcomes);

  const proposed = outcomeFor(outcomes, 'proposed');
  const claimable = canClaimBenefit(proposed);
  const blockedResult = RESULT_LABEL[proposed?.available && proposed.safety === 'fail' ? 'fail' : 'unknown'];
  const siteRisk = [benefits.siteRiskProbability, benefits.siteRiskExpectedMwh];
  const siteEstablished = siteRisk.some(hasValue);
  const benefitValues = [
    benefits.avoidedDispatchDownMwh,
    ...siteRisk,
    benefits.netSystemResourceCostEur,
    benefits.grossMarketOpportunityEur,
    benefits.netFinancialValueEur,
    benefits.carbonEffectTco2e,
  ];
  const noneEstablished = !benefitValues.some(hasValue);
  const collapsed = !claimable && noneEstablished;
  // Only cards with a number are greyed; a missing value has nothing to grey.
  const greyed = (...values: Established[]) => !claimable && values.some(hasValue);

  if (demo) {
    const available = columns.filter((item): item is OutcomeState => item !== undefined && item.available);
    const rows = [...SAFETY_ROWS, ...DISPATCH_DOWN_ROWS].filter((row) =>
      row.value && available.some((item) => hasValue(row.value!(item))));
    const metrics = [
      [BENEFIT_COPY.avoided, benefits.avoidedDispatchDownMwh],
      [BENEFIT_COPY.systemCost, benefits.netSystemResourceCostEur],
      [BENEFIT_COPY.marketOpportunity, benefits.grossMarketOpportunityEur],
      [BENEFIT_COPY.financialValue, benefits.netFinancialValueEur],
      [BENEFIT_COPY.carbon, benefits.carbonEffectTco2e],
    ] as const;
    const knownMetrics = metrics.filter((entry): entry is readonly [string, Established & { value: number }] => hasValue(entry[1]));
    if (!rows.length && !knownMetrics.length) return null;
    return (
      <section className="card comparison-panel" aria-labelledby="comparison-heading">
        <div className="panel-header"><h2 id="comparison-heading" className="panel-title">{COMPARISON_COPY.title}</h2></div>
        {rows.length > 0 && <div className="table-scroll"><table className="comparison-table">
          <thead><tr><th scope="col">{COMPARISON_COPY.measure}</th>{available.map((item) =>
            <th scope="col" key={item.column}>{COLUMN_LABEL[item.column]}</th>)}</tr></thead>
          <tbody>{rows.map((row) => <tr key={row.label}>
            <th scope="row">{row.label}</th>
            {available.map((item) => <td key={item.column}>{row.value && hasValue(row.value(item))
              ? formatWithUnit(row.value(item).value!, row.value(item).unit) : '—'}</td>)}
          </tr>)}</tbody>
        </table></div>}
        {knownMetrics.length > 0 && <dl className="metrics comparison-benefits">
          {knownMetrics.map(([name, value]) => <div className="metric established-card" key={name}>
            <dt className="metric-label">{name}</dt><dd className="established-value">{formatWithUnit(value.value, value.unit)}</dd>
          </div>)}
        </dl>}
      </section>
    );
  }

  const cards = (
    <dl className="metrics comparison-benefits">
      <EstablishedCard
        label={BENEFIT_COPY.avoided}
        entries={[{ value: benefits.avoidedDispatchDownMwh }]}
        details={[BENEFIT_COPY.avoidedDetail, BENEFIT_COPY.avoidedNote]}
        greyed={greyed(benefits.avoidedDispatchDownMwh)}
        requireRange
      />
      <EstablishedCard
        label={BENEFIT_COPY.siteRisk}
        entries={siteEstablished ? [
          { name: BENEFIT_COPY.siteProbability, value: benefits.siteRiskProbability },
          { name: BENEFIT_COPY.siteExpected, value: benefits.siteRiskExpectedMwh },
        ] : []}
        details={view === 'national' ? [BENEFIT_COPY.siteNationalView] : []}
        greyed={greyed(...siteRisk)}
      >
        {!siteEstablished && (
          <dd className="established-card-entry">
            <Missing />
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
        greyed={greyed(benefits.netSystemResourceCostEur)}
      />
      <EstablishedCard
        label={BENEFIT_COPY.marketOpportunity}
        entries={[{ value: benefits.grossMarketOpportunityEur }]}
        details={[BENEFIT_COPY.marketNote]}
        greyed={greyed(benefits.grossMarketOpportunityEur)}
      />
      <EstablishedCard
        label={BENEFIT_COPY.financialValue}
        entries={[{ value: benefits.netFinancialValueEur }]}
        details={[BENEFIT_COPY.perspective(benefits.netFinancialValueEur.perspective), BENEFIT_COPY.financialNote]}
        greyed={greyed(benefits.netFinancialValueEur)}
      />
      <EstablishedCard
        label={BENEFIT_COPY.carbon}
        entries={[{ value: benefits.carbonEffectTco2e }]}
        details={[BENEFIT_COPY.carbonNote]}
        greyed={greyed(benefits.carbonEffectTco2e)}
        requireRange
      />
    </dl>
  );

  return (
    <section className="card comparison-panel" aria-labelledby="comparison-heading">
      <div className="panel-header">
        <h2 id="comparison-heading" className="panel-title">{COMPARISON_COPY.title}</h2>
        {reference && (
          <span className="panel-meta comparison-window">
            {COMPARISON_COPY.window(formatWindow(reference.windowStart, reference.windowEnd))}
          </span>
        )}
      </div>
      {mismatched.length > 0 && (
        <p className="comparison-warning" role="alert">
          {COMPARISON_COPY.mismatch(mismatched.map((column) => COLUMN_LABEL[column]).join(', '))}
        </p>
      )}

      <div className="table-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">{COMPARISON_COPY.measure}</th>
              {COLUMN_ORDER.map((column) => (
                <th key={column} scope="col" className={column === BASELINE ? 'comparison-baseline' : undefined}>
                  <span className="comparison-column-name">{COLUMN_LABEL[column]}</span>
                  {column === BASELINE && <span className="comparison-baseline-tag">{COMPARISON_COPY.baselineTag}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <RowGroup title={COMPARISON_COPY.safetyGroup} rows={SAFETY_ROWS} columns={columns} />
          <RowGroup title={COMPARISON_COPY.dispatchDownGroup} rows={DISPATCH_DOWN_ROWS} columns={columns} />
        </table>
      </div>

      <h3 className="comparison-benefits-title">{BENEFIT_COPY.title}</h3>
      {collapsed ? (
        <>
          <p className="comparison-benefits-status">
            {proposed?.available ? BENEFIT_COPY.noneEstablished(blockedResult) : BENEFIT_COPY.noneEstablishedNoPlan}
          </p>
          <details className="disclosure comparison-benefits-details">
            <summary>{BENEFIT_COPY.showDetails}</summary>
            {cards}
          </details>
        </>
      ) : (
        cards
      )}
    </section>
  );
}

export default ComparisonPanel;

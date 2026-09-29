import type { ReactNode } from 'react';
import { ACTION_KIND_LABEL } from '../../decision/actionLabels';
import { DECISION_LABEL, EVIDENCE_COPY } from '../../decision/copy/evidence';
import { DATA_STATUS_LABEL, SOURCE_KIND_LABEL } from '../../decision/copy/shared';
import type { DataSourceKind, Evidence, OperatorEdit } from '../../decision/types';
import { formatDateTime } from '../../format';
import './EvidenceDrawer.css';

function formatWhen(iso: string | null): string {
  return iso ? formatDateTime(iso) : EVIDENCE_COPY.notRecorded;
}

function formatEditValue(value: number | string | null): string {
  return value === null || value === '' ? EVIDENCE_COPY.emptyValue : String(value);
}

// Plain list, or 'None listed' so an empty list is never mistaken for a
// hidden one.
function TextList({ items }: { items: string[] }) {
  if (!items.length) return <p className="evidence-empty">{EVIDENCE_COPY.none}</p>;
  return (
    <ul className="evidence-list">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}

// One row of the two-column layout: title left, content right. Stacks on
// narrow screens.
function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="evidence-section">
      <h3 className="evidence-heading">{title}</h3>
      <div className="evidence-content">{children}</div>
    </section>
  );
}

type Props = {
  evidence: Evidence;
  edits: OperatorEdit[];
  validated: boolean;
  sourceKind: DataSourceKind;
};

// Collapsed by default so the safety result is read first. Everything here
// explains the result; nothing here changes it.
function EvidenceDrawer({ evidence, edits, validated, sourceKind }: Props) {
  return (
    <details className="card evidence-drawer">
      <summary className="evidence-summary">
        <span className="panel-title evidence-summary-title">{EVIDENCE_COPY.summary}</span>
        <span className="panel-meta">{EVIDENCE_COPY.summaryHint}</span>
      </summary>
      <div className="evidence-body">
        <Section title={EVIDENCE_COPY.sourceTitle}>
          <p className="evidence-source">
            <span className={`chip ${sourceKind === 'live' ? 'chip-advisory' : 'chip-unknown'}`}>{SOURCE_KIND_LABEL[sourceKind]}</span>
            {validated && <span>{EVIDENCE_COPY.validated}</span>}
          </p>
          <dl className="evidence-fields">
            <div>
              <dt>{EVIDENCE_COPY.assessedAt}</dt>
              <dd>{formatWhen(evidence.assessedAt)}</dd>
            </div>
            <div>
              <dt>{EVIDENCE_COPY.auditId}</dt>
              <dd className="mono">{evidence.auditId ?? EVIDENCE_COPY.notRecorded}</dd>
            </div>
          </dl>
        </Section>

        <Section title={EVIDENCE_COPY.inputsTitle}>
          {evidence.inputs.length ? (
            <div className="table-scroll">
              <table className="evidence-table">
                <thead>
                  <tr>
                    <th scope="col">{EVIDENCE_COPY.inputColumns.label}</th>
                    <th scope="col">{EVIDENCE_COPY.inputColumns.source}</th>
                    <th scope="col">{EVIDENCE_COPY.inputColumns.time}</th>
                    <th scope="col">{EVIDENCE_COPY.inputColumns.edited}</th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.inputs.map((input) => (
                    <tr key={input.label}>
                      <th scope="row">{input.label}</th>
                      <td>{input.source}</td>
                      <td>{formatWhen(input.timestamp)}</td>
                      <td>
                        {input.editedByOperator
                          ? <span className="chip chip-advisory">{EVIDENCE_COPY.editedFlag}</span>
                          : EVIDENCE_COPY.notEdited}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="evidence-empty">{EVIDENCE_COPY.noInputs}</p>}
        </Section>

        <Section title={EVIDENCE_COPY.editsTitle}>
          {edits.length ? (
            <ul className="evidence-list">
              {edits.map((edit) => (
                <li key={`${edit.factId}-${edit.at}`}>
                  {EVIDENCE_COPY.edit(edit.label || edit.factId, formatEditValue(edit.from), formatEditValue(edit.to))}
                  <span className="evidence-meta"> · {formatWhen(edit.at)}</span>
                </li>
              ))}
            </ul>
          ) : <p className="evidence-empty">{EVIDENCE_COPY.noEdits}</p>}
        </Section>

        <Section title={EVIDENCE_COPY.versionsTitle}>
          <dl className="evidence-fields">
            <div>
              <dt>{EVIDENCE_COPY.ruleVersion}</dt>
              <dd>{evidence.ruleVersion ?? EVIDENCE_COPY.notRecorded}</dd>
            </div>
            <div>
              <dt>{EVIDENCE_COPY.modelVersions}</dt>
              <dd>{evidence.modelVersions.length ? evidence.modelVersions.join('; ') : EVIDENCE_COPY.notRecorded}</dd>
            </div>
          </dl>
        </Section>

        <Section title={EVIDENCE_COPY.limitsUsed}>
          <TextList items={evidence.limitsUsed} />
        </Section>

        <Section title={EVIDENCE_COPY.credibleFailuresUsed}>
          <TextList items={evidence.credibleFailuresUsed} />
        </Section>

        <Section title={EVIDENCE_COPY.actionsTitle}>
          {evidence.actionDecisions.length ? (
            <ul className="evidence-list evidence-actions">
              {evidence.actionDecisions.map((action) => (
                <li key={`${action.kind}-${action.stepId ?? 'none'}`}>
                  <span className={`evidence-decision evidence-decision-${action.decision}`}>{DECISION_LABEL[action.decision]}</span>
                  <span className="evidence-action-name">{ACTION_KIND_LABEL[action.kind]}</span>
                  {!action.stepId && <span className="evidence-meta"> ({EVIDENCE_COPY.notInPlan})</span>}
                  <span className="evidence-reason">{action.reason}</span>
                </li>
              ))}
            </ul>
          ) : <p className="evidence-empty">{EVIDENCE_COPY.noActions}</p>}
        </Section>

        <Section title={EVIDENCE_COPY.assumptionsTitle}>
          <TextList items={evidence.assumptions} />
        </Section>

        <Section title={EVIDENCE_COPY.uncertaintyTitle}>
          <TextList items={evidence.uncertainty} />
        </Section>

        <Section title={EVIDENCE_COPY.missingChecksTitle}>
          <TextList items={evidence.missingChecks} />
        </Section>

        <Section title={EVIDENCE_COPY.feedsTitle}>
          {evidence.feedFreshness.length ? (
            <ul className="evidence-list">
              {evidence.feedFreshness.map((feed) => (
                <li key={feed.feed}>
                  {feed.feed}:{' '}
                  <span className={`evidence-status evidence-status-${feed.status}`}>{DATA_STATUS_LABEL[feed.status]}</span>
                  <span className="evidence-meta"> · {EVIDENCE_COPY.asOf} {formatWhen(feed.asOf)}</span>
                </li>
              ))}
            </ul>
          ) : <p className="evidence-empty">{EVIDENCE_COPY.noFeeds}</p>}
        </Section>
      </div>
    </details>
  );
}

export default EvidenceDrawer;

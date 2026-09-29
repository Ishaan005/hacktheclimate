import { useState } from 'react';
import type { ReactNode } from 'react';
import { ACTION_FAMILY_LABEL, EXECUTABILITY_LABEL, WORKSPACE_COPY } from '../copy';
import { formatTime } from '../format';
import { instructionText } from '../scenarios';
import type { RecommendedAction } from '../types';
import ActionDetails from './ActionDetails';
import ActionTimeline from './ActionTimeline';

type Props = {
  action: RecommendedAction | null;
  noActionReason: string | null;
};

type Slide = {
  label: string;
  content: ReactNode;
};

// Shows the action detail one slide at a time, picked from a dropdown. Every slide sits in
// the same grid cell, so the carousel keeps the height of the tallest slide
// and the card does not resize between slides. Inactive slides are invisible
// and inert.
function ActionCarousel({ slides }: { slides: Slide[] }) {
  const [index, setIndex] = useState(0);
  return (
    <div
      className="action-carousel"
      role="group"
      aria-roledescription="carousel"
      aria-label={WORKSPACE_COPY.actionDetailsSummary}
    >
      <div className="action-carousel-nav">
        <select
          className="action-carousel-select"
          aria-label={WORKSPACE_COPY.actionDetailsSummary}
          value={index}
          onChange={(event) => setIndex(Number(event.target.value))}
        >
          {slides.map((slide, i) => (
            <option key={slide.label} value={i}>{slide.label}</option>
          ))}
        </select>
      </div>
      <div className="action-carousel-slides">
        {slides.map((slide, i) => (
          <div
            key={slide.label}
            className="action-carousel-slide"
            role="group"
            aria-roledescription="slide"
            aria-label={`${i + 1} of ${slides.length}: ${slide.label}`}
            aria-hidden={i !== index}
            inert={i !== index}
            style={i === index ? undefined : { visibility: 'hidden' }}
          >
            {slide.content}
          </div>
        ))}
      </div>
    </div>
  );
}

// Shared shell: the complete instruction and any conditional warning stay
// fixed at the top. The state change, schedule and family detail sit in a
// carousel below.
function RecommendedActionCard({ action, noActionReason }: Props) {
  if (!action) {
    return (
      <section className="card card-action card-action-none" aria-labelledby="action-heading">
        <h3 id="action-heading" className="card-kicker">{WORKSPACE_COPY.actionTitle}</h3>
        <p className="card-headline">{WORKSPACE_COPY.actionNone}</p>
        {noActionReason && <p>{noActionReason}</p>}
      </section>
    );
  }
  const conditional = action.executability === 'conditional';
  return (
    <section
      className={`card card-action${conditional ? ' card-action-conditional' : ''}`}
      aria-labelledby="action-heading"
    >
      <h3 id="action-heading" className="card-kicker">
        {WORKSPACE_COPY.actionTitle}
        <span className="chip chip-neutral">{ACTION_FAMILY_LABEL[action.family]}</span>
        <span className={`chip ${conditional ? 'chip-unknown' : 'chip-neutral'}`}>{EXECUTABILITY_LABEL[action.executability]}</span>
      </h3>
      <p className="instruction">{instructionText(action)}</p>
      {conditional && <p className="action-warning">{WORKSPACE_COPY.actionConditional}</p>}
      <ActionCarousel
        slides={[
          {
            label: WORKSPACE_COPY.actionSlideOverview,
            content: (
              <>
                <p className="state-change">
                  <span className="state-change-asset">{action.assetName} · {action.location}</span>
                  <span className="state-change-values">
                    <span className="state-change-from">{action.currentState}</span>
                    <span aria-hidden="true">→</span>
                    <span className="visually-hidden">to</span>
                    <span className="state-change-to">{action.targetState}</span>
                  </span>
                </p>
                <ActionTimeline action={action} />
              </>
            ),
          },
          {
            label: WORKSPACE_COPY.actionSlideSchedule,
            content: (
              <div className="action-detail">
                <dl className="fields fields-action">
                  <div><dt>Issue time</dt><dd className="mono">{formatTime(action.issueTime)}</dd></div>
                  <div><dt>Start time</dt><dd className="mono">{formatTime(action.startTime)}</dd></div>
                  <div><dt>Target achieved</dt><dd className="mono">{formatTime(action.targetTime)}</dd></div>
                  <div><dt>Effective until</dt><dd className="mono">{formatTime(action.effectiveUntil)}</dd></div>
                  <div>
                    <dt>Earliest achievable execution</dt>
                    <dd className="mono">{action.earliestExecution ? formatTime(action.earliestExecution) : 'Unknown'}</dd>
                  </div>
                </dl>
              </div>
            ),
          },
          { label: ACTION_FAMILY_LABEL[action.family], content: <ActionDetails action={action} part="fields" /> },
          { label: WORKSPACE_COPY.actionCostsTitle, content: <ActionDetails action={action} part="costs" /> },
        ]}
      />
    </section>
  );
}

export default RecommendedActionCard;

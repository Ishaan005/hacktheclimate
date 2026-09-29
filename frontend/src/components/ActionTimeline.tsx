import { formatTime, parseUtc } from '../format';
import type { RecommendedAction } from '../types';

type Event = { label: string; time: string };

// Horizontal strip of the action schedule: ramp from start to target, then
// hold until the action ends. Labels alternate above and below the track so
// close times (issue, start, target) do not collide.
function ActionTimeline({ action }: { action: RecommendedAction }) {
  const events: Event[] = [
    { label: 'Issued', time: action.issueTime },
    { label: 'Start', time: action.startTime },
    { label: 'Target reached', time: action.targetTime },
    { label: 'Effective until', time: action.effectiveUntil },
  ];
  if (action.earliestExecution && action.earliestExecution !== action.startTime) {
    events.push({ label: 'Earliest execution', time: action.earliestExecution });
  }
  const ms = (iso: string) => parseUtc(iso).getTime();
  const times = events.map((event) => ms(event.time));
  const min = Math.min(...times);
  const span = Math.max(...times) - min || 1;
  const pct = (iso: string) => ((ms(iso) - min) / span) * 100;
  const sorted = [...events].sort((a, b) => ms(a.time) - ms(b.time));

  return (
    <div className="timeline" aria-hidden="true">
      <div className="timeline-track">
        <span
          className="timeline-ramp"
          style={{ left: `${pct(action.startTime)}%`, width: `${pct(action.targetTime) - pct(action.startTime)}%` }}
          title={`Ramp ${formatTime(action.startTime)}–${formatTime(action.targetTime)}`}
        />
        <span
          className="timeline-hold"
          style={{ left: `${pct(action.targetTime)}%`, width: `${pct(action.effectiveUntil) - pct(action.targetTime)}%` }}
          title={`At target ${formatTime(action.targetTime)}–${formatTime(action.effectiveUntil)}`}
        />
        {sorted.map((event, index) => {
          const left = pct(event.time);
          const align = left < 12 ? 'start' : left > 88 ? 'end' : 'middle';
          return (
            <span
              key={event.label}
              className={`timeline-event timeline-event-${index % 2 ? 'below' : 'above'} timeline-event-${align}`}
              style={{ left: `${left}%` }}
            >
              <span className="timeline-event-label">{event.label}</span>
              <span className="timeline-event-time mono">{formatTime(event.time)}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default ActionTimeline;

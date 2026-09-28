import type { ForecastInterval } from '../types';
import { formatNumber, formatTime } from '../format';
import './ForecastTimeline.css';

// Plain SVG so the skeleton has no chart dependency. The viewBox scales to
// the container width; labels thin out to every 3 hours.

const WIDTH = 960;
const HEIGHT = 240;
const PLOT_TOP = 12;
const PLOT_BOTTOM = 170;
const STRIP_TOP = 184;
const STRIP_HEIGHT = 16;
const LABEL_Y = 226;

function ForecastTimeline({ intervals }: { intervals: ForecastInterval[] }) {
  const maxMwh = Math.max(
    10,
    ...intervals.map((item) => item.expected_constraint_mwh_upper ?? item.expected_constraint_mwh ?? 0),
  );
  const slot = WIDTH / Math.max(1, intervals.length);
  const barWidth = slot * 0.6;
  const y = (mwh: number) => PLOT_BOTTOM - (mwh / maxMwh) * (PLOT_BOTTOM - PLOT_TOP);
  const missing = intervals.filter((item) => item.expected_constraint_mwh === null).length;
  const horizons = intervals.map((item) => item.horizon_hours);
  const horizonText = horizons.length ? `${Math.min(...horizons)}–${Math.max(...horizons)} h ahead` : '';

  return (
    <figure className="timeline">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Half-hourly national constraint forecast, ${intervals.length} intervals, ${missing} unavailable. Bars show expected MWh with uncertainty range; strip shows event probability.`}
      >
        <line x1={0} x2={WIDTH} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM} className="timeline-axis" />
        {intervals.map((item, index) => {
          const x = index * slot + (slot - barWidth) / 2;
          const centre = index * slot + slot / 2;
          const { expected_constraint_mwh: p50, expected_constraint_mwh_lower: p10, expected_constraint_mwh_upper: p90 } = item;
          return (
            <g key={item.target_timestamp}>
              <title>
                {`${formatTime(item.target_timestamp)} UTC (${item.horizon_hours} h ahead): expected ${formatNumber(p50, 'MWh')}, range ${formatNumber(p10, 'MWh')}–${formatNumber(p90, 'MWh')}`}
              </title>
              {p50 === null ? (
                <rect x={x} y={PLOT_TOP} width={barWidth} height={PLOT_BOTTOM - PLOT_TOP} className="timeline-missing" />
              ) : (
                <rect x={x} y={y(p50)} width={barWidth} height={PLOT_BOTTOM - y(p50)} className="timeline-bar" />
              )}
              {p10 !== null && p90 !== null && (
                <line x1={centre} x2={centre} y1={y(p90)} y2={y(p10)} className="timeline-range" />
              )}
              <rect
                x={index * slot}
                y={STRIP_TOP}
                width={slot}
                height={STRIP_HEIGHT}
                className={item.event_probability === null ? 'timeline-missing' : 'timeline-probability'}
                style={item.event_probability === null ? undefined : { opacity: 0.1 + item.event_probability * 0.9 }}
              />
              {index % 6 === 0 && (
                <text x={centre} y={LABEL_Y} textAnchor="middle" className="timeline-label">
                  {formatTime(item.target_timestamp)}
                </text>
              )}
            </g>
          );
        })}
        <text x={4} y={PLOT_TOP + 10} className="timeline-label">{`${Math.round(maxMwh)} MWh`}</text>
      </svg>
      <figcaption className="timeline-legend">
        <span className="legend-bar">Expected MWh</span>
        <span className="legend-range">Uncertainty range</span>
        <span className="legend-probability">Probability of constraint event</span>
        <span className="legend-missing">Not available</span>
        <span>Times in UTC{horizonText && ` · ${horizonText}`}</span>
      </figcaption>
    </figure>
  );
}

export default ForecastTimeline;

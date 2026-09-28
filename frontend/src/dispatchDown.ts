import { USE_FIXTURE } from './mode';

export type DispatchDownRisk = 'low' | 'medium' | 'high';

export type DispatchDownForecast = {
  mode: string;
  input_timestamp: string;
  target_timestamp: string;
  horizon_hours: number;
  risk: DispatchDownRisk | string;
  event_probability: number;
  expected_dispatch_down_mwh: number;
  limitations: string[];
};

export const DEFAULT_TARGET = '2026-01-24T01:00';
// Range covered by the included January 2026 replay data (30-minute steps, UTC).
export const MIN_TARGET = '2026-01-01T01:00';
export const MAX_TARGET = '2026-01-31T23:30';

export function validateTarget(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) return 'Enter a date and time.';
  if (value < MIN_TARGET || value > MAX_TARGET) return 'Choose a time between 1 Jan 2026 01:00 and 31 Jan 2026 23:30 UTC.';
  const minutes = value.slice(14, 16);
  if (minutes !== '00' && minutes !== '30') return 'Use a time on the hour or half hour (for example 14:00 or 14:30).';
  return null;
}

export const fixtureDispatchDown: DispatchDownForecast = {
  mode: 'historical_replay',
  input_timestamp: '2026-01-24T00:00:00',
  target_timestamp: '2026-01-24T01:00:00',
  horizon_hours: 1,
  risk: 'high',
  event_probability: 0.9540596966110141,
  expected_dispatch_down_mwh: 37.20013258304385,
  limitations: [
    'This is a historical one-hour-ahead replay, not a live forecast.',
    'It forecasts national dispatch-down risk, not a specific transmission line or location.',
  ],
};

export async function fetchDispatchDown(target: string, signal?: AbortSignal): Promise<DispatchDownForecast> {
  if (USE_FIXTURE) return fixtureDispatchDown;
  const path = `/v1/dispatch-down/forecast?target_timestamp=${encodeURIComponent(`${target}:00Z`)}`;
  const response = await fetch(path, { signal });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      /* keep status */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<DispatchDownForecast>;
}

export type DispatchDownPoint = {
  target_timestamp: string;
  event_probability: number;
  expected_dispatch_down_mwh: number;
};

export type DispatchDownDay = {
  mode: string;
  date: string;
  horizon_hours: number;
  points: DispatchDownPoint[];
};

function fixtureDay(target: string): DispatchDownDay {
  const date = target.slice(0, 10);
  const points = Array.from({ length: 48 }, (_, i) => {
    const hh = String(Math.floor(i / 2)).padStart(2, '0');
    const mm = i % 2 ? '30' : '00';
    const p = Math.min(0.98, Math.max(0.02, 0.55 + 0.4 * Math.cos((i - 2) / 7)));
    return { target_timestamp: `${date}T${hh}:${mm}:00`, event_probability: p, expected_dispatch_down_mwh: p * 40 };
  });
  return { mode: 'historical_replay', date, horizon_hours: 1, points };
}

export async function fetchDispatchDownDay(target: string, signal?: AbortSignal): Promise<DispatchDownDay> {
  if (USE_FIXTURE) return fixtureDay(target);
  const path = `/v1/dispatch-down/forecast/day?target_timestamp=${encodeURIComponent(`${target}:00Z`)}`;
  const response = await fetch(path, { signal });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      /* keep status */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<DispatchDownDay>;
}

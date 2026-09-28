import { COPY } from './copy';

const timeFormat = new Intl.DateTimeFormat('en-IE', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
});

const dateTimeFormat = new Intl.DateTimeFormat('en-IE', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
});

// Historical API timestamps omit the zone but are UTC. Append Z so the
// browser does not read them as local time.
export function parseUtc(value: string): Date {
  return new Date(/(Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`);
}

export function formatTime(iso: string): string {
  return timeFormat.format(parseUtc(iso));
}

export function formatDateTime(iso: string | null): string {
  return iso ? `${dateTimeFormat.format(parseUtc(iso))} UTC` : COPY.notAvailable;
}

// Null means missing: never render it as zero.
export function formatNumber(value: number | null, unit: string, digits = 0): string {
  if (value === null || !Number.isFinite(value)) return COPY.notAvailable;
  return `${value.toFixed(digits)} ${unit}`;
}

export function formatPercent(value: number | null, digits = 0): string {
  if (value === null || !Number.isFinite(value)) return COPY.notAvailable;
  return `${value.toFixed(digits)}%`;
}

const eurFormat = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

export function formatEur(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return COPY.notAvailable;
  return eurFormat.format(value);
}

// Workspace times drop the UTC suffix; the scenario header states it once.
export function formatTimeRange(start: string, end: string): string {
  return `${formatTime(start)}–${formatTime(end)}`;
}

export function formatDayTime(iso: string | null): string {
  return iso ? dateTimeFormat.format(parseUtc(iso)) : COPY.notAvailable;
}

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

export function formatTime(iso: string): string {
  return timeFormat.format(new Date(iso));
}

export function formatDateTime(iso: string | null): string {
  return iso ? `${dateTimeFormat.format(new Date(iso))} UTC` : COPY.notAvailable;
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

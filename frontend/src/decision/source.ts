import type { DataSourceKind } from './types';

export function isDemoSource(kind: DataSourceKind): boolean {
  return kind === 'planning_case' || kind === 'historical_demo';
}

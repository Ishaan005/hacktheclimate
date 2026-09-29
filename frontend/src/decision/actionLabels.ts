// Plain-language names for each action kind, shared by the plan and safety
// panels.

import type { ActionKind } from './types';

export const ACTION_KIND_LABEL: Record<ActionKind, string> = {
  // Transmission
  paired_redispatch: 'Paired generator redispatch',
  switch_sectionalise: 'Switch or sectionalise the network',
  return_equipment_early: 'Return equipment from outage early',
  local_storage_or_demand: 'Local storage or demand response',
  wdt_limit: 'Wind dispatch limit (WDT)',
  interconnector_transfer: 'Change interconnector transfer',
  // High frequency / minimum generation
  fast_generation_reduction: 'Fast generation reduction',
  emergency_hvdc: 'Emergency HVDC action',
  swap_lower_minimum_unit: 'Swap to a unit with a lower minimum',
  replace_reserve_provider: 'Replace a reserve provider',
  commit_for_upward_ramp: 'Commit a unit for upward ramp',
  battery_charge_keep_service: 'Charge battery, keep its service',
  // SNSP
  snsp_interconnector: 'Interconnector change for SNSP',
  snsp_demand_release: 'Release demand for SNSP',
  snsp_all_island_wdt: 'All-island wind dispatch limit (WDT)',
};

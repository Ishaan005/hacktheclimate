import type { OutcomeState, ScenarioFamily } from './types';

export const IMPACT_FAMILIES: { id: ScenarioFamily; label: string; energyLabel: string }[] = [
  { id: 'transmission', label: 'Transmission constraint', energyLabel: 'Constrained energy' },
  { id: 'snsp', label: 'SNSP', energyLabel: 'Curtailed energy' },
  { id: 'high_frequency_minimum_generation', label: 'High frequency / minimum generation', energyLabel: 'Curtailed energy' },
];

export const EXAMPLE_ENERGY_MWH = 10;
export const EXAMPLE_VALUE_EUR_PER_MWH = 100;
export const EXAMPLE_DISPLACEMENT_TCO2_PER_MWH = 0.35;

export function comparisonEnergy(
  outcomes: OutcomeState[], family: ScenarioFamily,
): number | null {
  const baseline = outcomes.find((item) => item.column === 'no_new_instruction');
  const proposed = outcomes.find((item) => item.column === 'proposed');
  if (!baseline?.available || !proposed?.available
    || baseline.windowStart !== proposed.windowStart || baseline.windowEnd !== proposed.windowEnd
    || !baseline.includesActiveInstructions || !proposed.includesActiveInstructions) return null;

  const key = family === 'transmission' ? 'constrainedMwh' : 'curtailedMwh';
  const before = baseline[key].value;
  const after = proposed[key].value;
  if (before === null || after === null || !Number.isFinite(before) || !Number.isFinite(after)
    || before < 0 || after < 0 || after > before) return null;
  return before - after;
}

export function illustrativeImpact(energyMwh: number, eurPerMwh: number, tco2PerMwh: number, planCostEur: number) {
  if (![energyMwh, eurPerMwh, tco2PerMwh, planCostEur].every((value) => Number.isFinite(value) && value >= 0)) return null;
  const grossEnergyValueEur = energyMwh * eurPerMwh;
  return {
    grossEnergyValueEur,
    netScenarioValueEur: grossEnergyValueEur - planCostEur,
    displacementPotentialTco2: energyMwh * tco2PerMwh,
  };
}

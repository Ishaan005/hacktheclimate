import { comparisonEnergy, EXAMPLE_DISPLACEMENT_TCO2_PER_MWH, EXAMPLE_VALUE_EUR_PER_MWH, illustrativeImpact } from '../../decision/impact';
import type { OutcomeState, ScenarioFamily } from '../../decision/types';
import { formatEur } from '../../format';

type Props = { outcomes: OutcomeState[]; families: ScenarioFamily[] };

export default function ImpactCalculator({ outcomes, families }: Props) {
  const energy = comparisonEnergy(outcomes, families[0] ?? 'transmission');
  const impact = energy === null ? null
    : illustrativeImpact(energy, EXAMPLE_VALUE_EUR_PER_MWH, EXAMPLE_DISPLACEMENT_TCO2_PER_MWH, 0);

  return (
    <section className="impact-calculator" aria-label="Illustrative energy impact">
      <h3 className="comparison-benefits-title">Illustrative energy impact</h3>
      <div className="impact-results">
        <div><span>Gross energy value</span><strong>{impact ? formatEur(impact.grossEnergyValueEur) : '—'}</strong></div>
        <div><span>Illustrative saving after plan cost</span><strong>{impact ? formatEur(impact.netScenarioValueEur) : '—'}</strong></div>
        <div><span>CO₂ displacement potential</span><strong>{impact ? `${impact.displacementPotentialTco2.toFixed(1)} tCO₂` : '—'}</strong></div>
      </div>
    </section>
  );
}

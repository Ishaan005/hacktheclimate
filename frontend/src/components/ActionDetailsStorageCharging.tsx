import { COPY } from '../copy';
import { formatEur, formatNumber, formatPercent } from '../format';
import type { StorageChargingDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';
import type { DetailPart } from './ActionDetailFields';

function stateOfChargeRange({ minStateOfChargePct: min, maxStateOfChargePct: max }: StorageChargingDetails): string {
  if (min === null || max === null) return COPY.notAvailable;
  return `${formatPercent(min)}–${formatPercent(max)}`;
}

function ActionDetailsStorageCharging({ details, part }: { details: StorageChargingDetails; part: DetailPart }) {
  return (
    <ActionDetailFields
      part={part}
      fields={[
        { label: 'Current state of charge', value: formatPercent(details.stateOfChargePct), mono: true },
        { label: 'State of charge limits', value: stateOfChargeRange(details), mono: true },
        { label: 'Charging target', value: formatNumber(details.chargingTargetMw, 'MW'), mono: true },
        { label: 'Available charging energy', value: formatNumber(details.availableChargingMwh, 'MWh'), mono: true },
        { label: 'Ramp rate', value: formatNumber(details.rampRateMwPerMin, 'MW/min', 1), mono: true },
        { label: 'Round-trip efficiency', value: formatPercent(details.roundTripEfficiencyPct), mono: true },
        { label: 'Rebound requirement', value: details.reboundRequirement ?? COPY.notAvailable },
      ]}
      costs={[
        { label: 'Charging cost', value: formatEur(details.chargingCostEur), mono: true },
        { label: 'Loss cost', value: formatEur(details.lossCostEur), mono: true },
        { label: 'Degradation cost', value: formatEur(details.degradationCostEur), mono: true },
      ]}
    />
  );
}

export default ActionDetailsStorageCharging;

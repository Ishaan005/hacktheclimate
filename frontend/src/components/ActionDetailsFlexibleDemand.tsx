import { COPY, DEMAND_DIRECTION_LABEL } from '../copy';
import { formatEur, formatNumber } from '../format';
import type { FlexibleDemandDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';

function ActionDetailsFlexibleDemand({ details }: { details: FlexibleDemandDetails }) {
  return (
    <ActionDetailFields
      fields={[
        { label: 'Direction', value: details.direction ? DEMAND_DIRECTION_LABEL[details.direction] : COPY.notAvailable },
        { label: 'Demand change', value: formatNumber(details.changeMw, 'MW'), mono: true },
        { label: 'Available energy to move', value: formatNumber(details.availableMwh, 'MWh'), mono: true },
        { label: 'Normal demand baseline', value: formatNumber(details.demandBaselineMw, 'MW'), mono: true },
        { label: 'Activation delay', value: formatNumber(details.activationDelayMinutes, 'min'), mono: true },
        { label: 'Maximum duration', value: formatNumber(details.maxDurationMinutes, 'min'), mono: true },
        { label: 'Constraint relief per MW', value: formatNumber(details.constraintReliefPerMw, 'MW/MW', 2), mono: true },
        { label: 'Rebound requirement', value: details.reboundRequirement ?? COPY.notAvailable },
      ]}
      costs={[
        { label: 'Activation cost', value: formatEur(details.activationCostEur), mono: true },
        { label: 'Rebound-energy cost', value: formatEur(details.reboundCostEur), mono: true },
      ]}
    />
  );
}

export default ActionDetailsFlexibleDemand;

import { COORDINATION_LABEL, COPY } from '../copy';
import { formatEur, formatNumber, formatTime } from '../format';
import type { InterconnectorRequestDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';

function ActionDetailsInterconnectorRequest({ details }: { details: InterconnectorRequestDetails }) {
  return (
    <ActionDetailFields
      fields={[
        { label: 'Interconnector', value: details.interconnector ?? COPY.notAvailable },
        { label: 'Direction', value: details.direction ?? COPY.notAvailable },
        { label: 'Requested flow', value: formatNumber(details.requestedMw, 'MW'), mono: true },
        { label: 'Existing scheduled flow', value: formatNumber(details.scheduledFlowMw, 'MW'), mono: true },
        { label: 'Transfer capacity', value: formatNumber(details.transferCapacityMw, 'MW'), mono: true },
        { label: 'Ramp limit', value: formatNumber(details.rampLimitMwPerMin, 'MW/min', 1), mono: true },
        {
          label: 'Earliest feasible interval',
          value: details.earliestFeasibleInterval ? formatTime(details.earliestFeasibleInterval) : COPY.notAvailable,
          mono: true,
        },
        { label: 'Counterparty coordination', value: COORDINATION_LABEL[details.coordinationStatus] },
      ]}
      costs={[{ label: 'Cross-border action cost', value: formatEur(details.crossBorderCostEur), mono: true }]}
    />
  );
}

export default ActionDetailsInterconnectorRequest;

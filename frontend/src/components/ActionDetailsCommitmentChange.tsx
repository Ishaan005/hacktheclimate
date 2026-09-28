import { COMMITMENT_LABEL, COPY, THERMAL_STATE_LABEL } from '../copy';
import { formatEur, formatNumber } from '../format';
import type { CommitmentChangeDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';

function ActionDetailsCommitmentChange({ details }: { details: CommitmentChangeDetails }) {
  const starting = details.targetCommitment === 'online';
  return (
    <ActionDetailFields
      fields={[
        {
          label: 'Current commitment',
          value: details.currentCommitment ? COMMITMENT_LABEL[details.currentCommitment] : COPY.notAvailable,
        },
        {
          label: 'Target commitment',
          value: details.targetCommitment ? COMMITMENT_LABEL[details.targetCommitment] : COPY.notAvailable,
        },
        {
          label: 'Hot, warm or cold',
          value: details.thermalState ? THERMAL_STATE_LABEL[details.thermalState] : COPY.notAvailable,
        },
        {
          label: starting ? 'Synchronisation time' : 'Shutdown time',
          value: formatNumber(details.transitionMinutes, 'min'),
          mono: true,
        },
        { label: 'Minimum on time', value: formatNumber(details.minOnHours, 'h', 1), mono: true },
        { label: 'Minimum off time', value: formatNumber(details.minOffHours, 'h', 1), mono: true },
        { label: 'Inertia contribution', value: formatNumber(details.inertiaContributionMws, 'MWs'), mono: true },
        { label: 'Reserve contribution', value: formatNumber(details.reserveContributionMw, 'MW'), mono: true },
        { label: 'Reactive contribution', value: formatNumber(details.reactiveContributionMvar, 'Mvar'), mono: true },
      ]}
      costs={[
        { label: 'Start cost', value: formatEur(details.startCostEur), mono: true },
        { label: 'Stop cost', value: formatEur(details.stopCostEur), mono: true },
        { label: 'Minimum-run cost', value: formatEur(details.minimumRunCostEur), mono: true },
      ]}
    />
  );
}

export default ActionDetailsCommitmentChange;

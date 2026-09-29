import { COPY } from '../copy';
import { formatList, formatNumber, formatTime } from '../format';
import type { RenewableLimitDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';

type Props = {
  details: RenewableLimitDetails;
  startTime: string;
  endTime: string;
};

function ActionDetailsRenewableLimit({ details, startTime, endTime }: Props) {
  return (
    <ActionDetailFields
      fields={[
        { label: 'Constraint group', value: details.constraintGroup ?? COPY.notAvailable },
        { label: 'Affected units', value: formatList(details.affectedUnits) },
        { label: 'Total reduction', value: formatNumber(details.totalReductionMw, 'MW'), mono: true },
        { label: 'Limit start', value: formatTime(startTime), mono: true },
        { label: 'Limit end', value: formatTime(endTime), mono: true },
        { label: 'Dispatch reason', value: details.dispatchReason ?? COPY.notAvailable },
        {
          label: 'Expected dispatch-down waste',
          value: formatNumber(details.expectedDispatchDownWasteMwh, 'MWh'),
          mono: true,
        },
        { label: 'Remaining security margin', value: details.remainingSecurityMargin ?? COPY.notAvailable },
      ]}
    />
  );
}

export default ActionDetailsRenewableLimit;

import { COPY } from '../copy';
import { formatDateTime, formatEur, formatList, formatNumber } from '../format';
import type { OutageReviewDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';

// A publication lists planned work; it is not proof of the actual switch
// state, so the status is shown as published.
function ActionDetailsOutageReview({ details }: { details: OutageReviewDetails }) {
  return (
    <ActionDetailFields
      fields={[
        { label: 'Outage ID', value: details.outageId ?? COPY.notAvailable, mono: true },
        { label: 'Equipment', value: details.equipmentDescription ?? COPY.notAvailable },
        { label: 'Scheduled start', value: formatDateTime(details.scheduledStart), mono: true },
        { label: 'Scheduled finish', value: formatDateTime(details.scheduledEnd), mono: true },
        { label: 'Published', value: formatDateTime(details.publicationDate), mono: true },
        { label: 'Published status', value: details.outageStatus ?? COPY.notAvailable },
        { label: 'Reviewed model asset', value: details.reviewedModelAsset ?? COPY.notAvailable },
        { label: 'Asset-match confidence', value: details.assetMatchConfidence ?? COPY.notAvailable },
        { label: 'Alternative window', value: details.alternativeWindow ?? COPY.notAvailable },
        { label: 'Overlapping outages', value: formatList(details.overlappingOutages) },
        { label: 'Additional exposure from the outage', value: formatNumber(details.additionalExposureMwh, 'MWh'), mono: true },
      ]}
      costs={[{ label: 'Financial exposure from the outage', value: formatEur(details.financialExposureEur), mono: true }]}
    />
  );
}

export default ActionDetailsOutageReview;

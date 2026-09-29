import { COPY } from '../copy';
import { formatEur, formatList, formatNumber } from '../format';
import type { GeneratorRedispatchDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';
import type { DetailPart } from './ActionDetailFields';

function ActionDetailsGeneratorRedispatch({ details, part }: { details: GeneratorRedispatchDetails; part: DetailPart }) {
  return (
    <ActionDetailFields
      part={part}
      fields={[
        { label: 'Current output', value: formatNumber(details.currentMw, 'MW'), mono: true },
        { label: 'Target output', value: formatNumber(details.targetMw, 'MW'), mono: true },
        { label: 'Ramp rate', value: formatNumber(details.rampRateMwPerMin, 'MW/min', 1), mono: true },
        { label: 'Minimum stable generation', value: formatNumber(details.minStableGenerationMw, 'MW'), mono: true },
        { label: 'Maximum output', value: formatNumber(details.maxOutputMw, 'MW'), mono: true },
        { label: 'Start and stop restrictions', value: details.startStopRestrictions ?? COPY.notAvailable },
        { label: 'Services retained', value: formatList(details.servicesRetained) },
        { label: 'Services lost', value: formatList(details.servicesLost) },
      ]}
      costs={[{ label: 'Estimated redispatch cost', value: formatEur(details.redispatchCostEur), mono: true }]}
    />
  );
}

export default ActionDetailsGeneratorRedispatch;

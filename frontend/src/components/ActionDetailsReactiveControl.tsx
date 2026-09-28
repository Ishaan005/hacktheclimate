import { COPY } from '../copy';
import { formatNumber, formatSigned } from '../format';
import type { ReactiveControlDetails } from '../types';
import ActionDetailFields from './ActionDetailFields';

function capability({ capabilityMinMvar: min, capabilityMaxMvar: max, presentMw }: ReactiveControlDetails): string {
  if (min === null || max === null) return COPY.notAvailable;
  const range = `${formatSigned(min, 'Mvar')} to ${formatSigned(max, 'Mvar')}`;
  return presentMw === null ? range : `${range} at ${formatNumber(presentMw, 'MW')}`;
}

function tap(position: number | null): string {
  return position === null ? COPY.notAvailable : String(position);
}

function ActionDetailsReactiveControl({ details }: { details: ReactiveControlDetails }) {
  return (
    <ActionDetailFields
      fields={[
        { label: 'Current voltage', value: formatNumber(details.currentVoltageKv, 'kV', 1), mono: true },
        { label: 'Target voltage', value: formatNumber(details.targetVoltageKv, 'kV', 1), mono: true },
        { label: 'Current reactive power', value: formatSigned(details.currentMvar, 'Mvar'), mono: true },
        { label: 'Target reactive power', value: formatSigned(details.targetMvar, 'Mvar'), mono: true },
        { label: 'Reactive capability at present output', value: capability(details), mono: true },
        { label: 'Tap position', value: `${tap(details.currentTapPosition)} to ${tap(details.targetTapPosition)}`, mono: true },
        { label: 'Response time', value: formatNumber(details.responseTimeSeconds, 's'), mono: true },
        { label: 'Expected voltage-margin improvement', value: details.voltageMarginImprovement ?? COPY.notAvailable },
        { label: 'Side effects elsewhere', value: details.sideEffects ?? COPY.notAvailable },
      ]}
    />
  );
}

export default ActionDetailsReactiveControl;

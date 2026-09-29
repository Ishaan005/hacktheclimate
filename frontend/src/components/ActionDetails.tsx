import type { RecommendedAction } from '../types';
import ActionDetailsCommitmentChange from './ActionDetailsCommitmentChange';
import ActionDetailsGeneratorSetpoint from './ActionDetailsGeneratorSetpoint';
import ActionDetailsInterconnectorRequest from './ActionDetailsInterconnectorRequest';
import ActionDetailsReactiveControl from './ActionDetailsReactiveControl';
import ActionDetailsRenewableLimit from './ActionDetailsRenewableLimit';
import ActionDetailsStorageCharging from './ActionDetailsStorageCharging';

// Picks the family-specific module rendered inside the shared action shell.
function ActionDetails({ action }: { action: RecommendedAction }) {
  switch (action.family) {
    case 'generator_setpoint':
      return <ActionDetailsGeneratorSetpoint details={action.details} />;
    case 'commitment_change':
      return <ActionDetailsCommitmentChange details={action.details} />;
    case 'storage_charging':
      return <ActionDetailsStorageCharging details={action.details} />;
    case 'reactive_control':
      return <ActionDetailsReactiveControl details={action.details} />;
    case 'renewable_limit':
      return <ActionDetailsRenewableLimit details={action.details} startTime={action.startTime} endTime={action.effectiveUntil} />;
    case 'interconnector_request':
      return <ActionDetailsInterconnectorRequest details={action.details} />;
  }
}

export default ActionDetails;

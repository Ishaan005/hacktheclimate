import type { RecommendedAction } from '../types';
import ActionDetailsFlexibleDemand from './ActionDetailsFlexibleDemand';
import ActionDetailsGeneratorRedispatch from './ActionDetailsGeneratorRedispatch';
import ActionDetailsOutageReview from './ActionDetailsOutageReview';
import ActionDetailsStorageCharging from './ActionDetailsStorageCharging';

// Picks the family-specific module rendered inside the shared action shell.
function ActionDetails({ action }: { action: RecommendedAction }) {
  switch (action.family) {
    case 'storage_charging':
      return <ActionDetailsStorageCharging details={action.details} />;
    case 'flexible_demand':
      return <ActionDetailsFlexibleDemand details={action.details} />;
    case 'generator_redispatch':
      return <ActionDetailsGeneratorRedispatch details={action.details} />;
    case 'outage_review':
      return <ActionDetailsOutageReview details={action.details} />;
  }
}

export default ActionDetails;

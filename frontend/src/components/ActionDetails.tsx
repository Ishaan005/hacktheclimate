import type { RecommendedAction } from '../types';
import ActionDetailsFlexibleDemand from './ActionDetailsFlexibleDemand';
import ActionDetailsGeneratorRedispatch from './ActionDetailsGeneratorRedispatch';
import ActionDetailsOutageReview from './ActionDetailsOutageReview';
import ActionDetailsStorageCharging from './ActionDetailsStorageCharging';
import type { DetailPart } from './ActionDetailFields';

// Picks the family-specific module rendered inside the shared action shell.
function ActionDetails({ action, part }: { action: RecommendedAction; part: DetailPart }) {
  switch (action.family) {
    case 'storage_charging':
      return <ActionDetailsStorageCharging details={action.details} part={part} />;
    case 'flexible_demand':
      return <ActionDetailsFlexibleDemand details={action.details} part={part} />;
    case 'generator_redispatch':
      return <ActionDetailsGeneratorRedispatch details={action.details} part={part} />;
    case 'outage_review':
      return <ActionDetailsOutageReview details={action.details} part={part} />;
  }
}

export default ActionDetails;

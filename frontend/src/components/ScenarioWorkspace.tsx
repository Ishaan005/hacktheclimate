import type { WorkspaceScenario } from '../types';
import AlternativeActionsPanel from './AlternativeActionsPanel';
import BindingConditionCard from './BindingConditionCard';
import GuardrailStrip from './GuardrailStrip';
import OutcomeComparisonPanel from './OutcomeComparisonPanel';
import RecommendedActionCard from './RecommendedActionCard';
import ScenarioHeader from './ScenarioHeader';
import './ScenarioWorkspace.css';

// Scenario → Binding condition → Recommended action → New outcome, then the
// lower-ranked alternatives last so the recommendation leads.
function ScenarioWorkspace({ scenario }: { scenario: WorkspaceScenario }) {
  return (
    <section className="workspace" aria-labelledby="workspace-heading">
      <ScenarioHeader scenario={scenario} />
      <div className="workspace-flow">
        <BindingConditionCard binding={scenario.binding} />
        <RecommendedActionCard
          action={scenario.action}
          noActionReason={scenario.noActionReason}
          reasons={scenario.recommendationReasons}
          alternativeCount={scenario.alternatives.length}
        />
      </div>
      <OutcomeComparisonPanel scenario={scenario} />
      <GuardrailStrip guardrails={scenario.guardrails} />
      <AlternativeActionsPanel alternatives={scenario.alternatives} hasRecommendation={scenario.action !== null} />
    </section>
  );
}

export default ScenarioWorkspace;

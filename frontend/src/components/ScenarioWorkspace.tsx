import type { WorkspaceScenario } from '../types';
import BindingConditionCard from './BindingConditionCard';
import DemoAssistantCard from './DemoAssistantCard';
import GuardrailStrip from './GuardrailStrip';
import OutcomeComparisonPanel from './OutcomeComparisonPanel';
import RecommendedActionCard from './RecommendedActionCard';
import ScenarioHeader from './ScenarioHeader';
import './ScenarioWorkspace.css';

// Scenario → Binding condition → Recommended action → New outcome.
function ScenarioWorkspace({ scenario, operatorCase }: { scenario: WorkspaceScenario; operatorCase?: unknown }) {
  return (
    <section className="workspace" aria-labelledby="workspace-heading">
      <ScenarioHeader scenario={scenario} />
      <div className="workspace-flow">
        <BindingConditionCard binding={scenario.binding} />
        <RecommendedActionCard
          action={scenario.action}
          noActionReason={scenario.noActionReason}
          presentation={scenario.actionPresentation}
        />
      </div>
      <OutcomeComparisonPanel scenario={scenario} />
      <GuardrailStrip guardrails={scenario.guardrails} />
      {scenario.source === 'demo' && operatorCase != null && <DemoAssistantCard operatorCase={operatorCase} />}
    </section>
  );
}

export default ScenarioWorkspace;

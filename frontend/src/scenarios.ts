// Scenario helpers for the workspace. In live use an LLM solver returns the
// scenario (see solveSituation in api.ts); resolveSituation below only backs
// the offline fixture.

import { formatTime } from './format';
import { DEFAULT_TARGET, validateTarget } from './dispatchDown';
import { answerLabel } from './clarification';
import { illustrativeClarification } from './fixtures/illustrativeClarification';
import type { Executability, RecommendedAction, SolverRequest, SolverResult, WorkspaceScenario } from './types';

// Reads like a dispatch instruction, e.g.
// "Issued 14:55 — Generator A to 100 MW by 15:10, effective until 16:30."
// An interconnector change is a request to a counterparty, so it says so.
export function instructionText(action: RecommendedAction): string {
  const verb = action.family === 'interconnector_request' ? 'Requested' : 'Issued';
  return `${verb} ${formatTime(action.issueTime)} — ${action.assetName} to ${action.targetState} by ${formatTime(action.targetTime)}, effective until ${formatTime(action.effectiveUntil)}.`;
}

// An interconnector request is never shown as executable until the
// counterparty confirms it, whatever the solver reported.
export function effectiveExecutability(action: RecommendedAction): Executability {
  if (action.family === 'interconnector_request' && action.details.coordinationStatus !== 'confirmed') {
    return 'unconfirmed';
  }
  return action.executability;
}

// Avoided waste needs both states. Null when either is unknown.
export function avoidedWasteMwh(scenario: WorkspaceScenario): number | null {
  const before = scenario.baseline.dispatchDownWasteMwh;
  const after = scenario.postAction?.dispatchDownWasteMwh ?? null;
  if (before === null || after === null) return null;
  return before - after;
}

// Percentage reduction. 'n/a' when baseline waste is zero: there is nothing
// to reduce, which is different from a zero reduction.
export function dispatchDownReductionPct(scenario: WorkspaceScenario): number | null | 'n/a' {
  const avoided = avoidedWasteMwh(scenario);
  if (avoided === null) return null;
  if (scenario.baseline.dispatchDownWasteMwh === 0) return 'n/a';
  return (avoided / (scenario.baseline.dispatchDownWasteMwh as number)) * 100;
}

const STOP_WORDS = new Set(['the', 'and', 'for', 'with', 'are', 'has', 'have', 'from', 'into', 'its', 'our', 'this', 'that', 'there', 'after', 'about']);

function words(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9]+/g)?.filter((word) => word.length >= 3 && !STOP_WORDS.has(word)) ?? [];
}

function scenarioText(scenario: WorkspaceScenario): string {
  return [
    scenario.title,
    scenario.summary,
    ...scenario.keywords,
    scenario.binding?.type,
    scenario.binding?.metric,
    scenario.binding?.location,
    scenario.action?.assetName,
    scenario.action?.location,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

// Offline fixture only: deterministic keyword match against illustrative
// scenarios. It does not run a study; an unmatched description returns null.
export function resolveSituation(description: string, scenarios: WorkspaceScenario[]): WorkspaceScenario | null {
  const query = new Set(words(description));
  if (!query.size) return null;
  let best: WorkspaceScenario | null = null;
  let bestScore = 0;
  for (const scenario of scenarios) {
    const haystack = new Set(words(scenarioText(scenario)));
    let score = 0;
    for (const word of query) if (haystack.has(word)) score += 1;
    if (score > bestScore) {
      best = scenario;
      bestScore = score;
    }
  }
  return best;
}

// Loose on purpose: operators say "DD", "risk next hour" or "show the graph".
const DISPATCH_DOWN_PATTERN = /\b(dispatch[\s-]*down|dispatch|dd|risk|forecast|graph|chart|next[\s-]*hour)\b/i;
const TARGET_PATTERN = /(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/;

// Descriptions that name no limit, area or asset. The offline solver asks
// follow-up questions for these instead of guessing.
const VAGUE_PATTERN = /\b(problem|issue|help|alarm|alert|something|not sure|unsure)\b/i;

// Offline fixture only: questions about dispatch-down risk get the replay
// view, at the time named in the description when it is a valid replay
// half-hour. A vague first description gets the illustrative follow-up
// questions; answers are appended to the description and matched against the
// illustrative scenarios.
export function resolveFixtureSolver(request: SolverRequest, scenarios: WorkspaceScenario[]): SolverResult | null {
  const { description, answers } = request;
  if (DISPATCH_DOWN_PATTERN.test(description)) {
    const match = description.match(TARGET_PATTERN);
    const named = match ? `${match[1]}T${match[2]}` : null;
    return { kind: 'dispatch_down_risk', target: named && !validateTarget(named) ? named : DEFAULT_TARGET };
  }
  if (!answers.length && VAGUE_PATTERN.test(description)) {
    return { kind: 'clarification', threadId: null, clarification: illustrativeClarification };
  }
  const answered = answers.map((answer) => {
    const question = illustrativeClarification.questions.find((item) => item.id === answer.questionId);
    return question ? answerLabel(question, answer.value) : null;
  });
  const scenario = resolveSituation([description, ...answered].filter(Boolean).join(' '), scenarios);
  return scenario ? { kind: 'scenario', scenario } : null;
}

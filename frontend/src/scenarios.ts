// Scenario helpers for the workspace. In live use an LLM solver returns the
// scenario (see solveSituation in api.ts); resolveSituation below only backs
// the offline fixture.

import { formatTime } from './format';
import type { RecommendedAction, WorkspaceScenario } from './types';

// Reads like a dispatch instruction, e.g.
// "Issued 14:55 — Generator A to 100 MW by 15:10, effective until 16:30."
export function instructionText(action: RecommendedAction): string {
  return `Issued ${formatTime(action.issueTime)} — ${action.assetName} to ${action.targetState} by ${formatTime(action.targetTime)}, effective until ${formatTime(action.effectiveUntil)}.`;
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

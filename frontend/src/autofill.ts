// Fills empty situation facts automatically so the review table starts with
// values instead of "Unknown". Every value filled here is marked as system
// inferred or forecast, with its source, so the operator can still correct it.
// Facts the operator (or intake) already supplied are never overwritten.

import { isMissing, type Fact, type FactSource, type FactStatus, type FactValue, type OperatorCase, type ScenarioFamily } from './case';
import { DEFAULT_TARGET, fetchDispatchDown, fetchDispatchDownDay, type DispatchDownForecast, type DispatchDownDay } from './dispatchDown';
import { namedTarget } from './scenarios';

const MODEL_NAME = 'Dispatch-down model (historical replay)';

function autoFact(key: string, value: FactValue, unit: string | null, status: FactStatus, source: FactSource, sourceName: string, asOf: string): Fact {
  return { key, value, unit, status, source, sourceName, asOf, history: [] };
}

function addHalfHour(target: string): string {
  const [h, m] = target.slice(11, 16).split(':').map(Number);
  const total = h * 60 + m + 30;
  return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

// Keyword reading of the description. Falls back to the forecast: a likely
// national dispatch-down event points to system-wide curtailment.
export function inferScenario(text: string, forecast: DispatchDownForecast | null): ScenarioFamily | null {
  const t = text.toLowerCase();
  if (/outage|maintenance|planned work/.test(t)) return 'planned_outage_exposure';
  if (/constraint|congest|\bline\b|substation|circuit|thermal|local/.test(t)) return 'local_network_constraint';
  if (/curtail|snsp|surplus|oversupply|system[- ]wide|national|wind/.test(t)) return 'system_wide_curtailment';
  if (forecast && forecast.event_probability >= 0.5) return 'system_wide_curtailment';
  return null;
}

function forecastRange(day: DispatchDownDay | null, target: string): string | null {
  if (!day?.points?.length) return null;
  const t = Date.parse(`${target}:00Z`);
  const near = day.points.filter((p) => Math.abs(Date.parse(`${p.target_timestamp.slice(0, 19)}Z`) - t) <= 60 * 60 * 1000);
  const values = (near.length ? near : day.points).map((p) => p.expected_dispatch_down_mwh);
  return `${Math.min(...values).toFixed(1)}–${Math.max(...values).toFixed(1)}`;
}

export async function autofillSituation(operatorCase: OperatorCase, signal?: AbortSignal): Promise<OperatorCase> {
  const now = new Date().toISOString();
  const named = namedTarget(operatorCase.originalText);
  const target = named ?? DEFAULT_TARGET;
  const [forecast, day] = await Promise.all([
    fetchDispatchDown(target, signal).catch(() => null),
    fetchDispatchDownDay(target, signal).catch(() => null),
  ]);
  const issued = forecast?.input_timestamp ? `${forecast.input_timestamp.slice(0, 19)}Z` : now;
  const facts = { ...operatorCase.facts };
  const fill = (fact: Fact) => {
    if (isMissing(facts[fact.key])) facts[fact.key] = fact;
  };

  fill(autoFact('event_window', `${target.slice(0, 10)} ${target.slice(11, 16)}–${addHalfHour(target)} UTC`, null,
    'system_inferred', named ? 'operator' : 'forecast', named ? 'Read from the operator description' : 'Default replay interval', now));
  fill(autoFact('affected_area', 'All-island (national)', null, 'system_inferred', 'forecast',
    'Dispatch-down model is national, not location specific', now));
  if (forecast) {
    fill(autoFact('expected_dispatch_down_mwh', Math.round(forecast.expected_dispatch_down_mwh * 10) / 10, 'MWh', 'forecast', 'forecast', MODEL_NAME, issued));
    fill(autoFact('event_probability', Math.round(forecast.event_probability * 100), '%', 'forecast', 'forecast', MODEL_NAME, issued));
  }
  const range = forecastRange(day, target);
  if (range) fill(autoFact('forecast_range_mwh', range, 'MWh', 'forecast', 'forecast', `${MODEL_NAME}, ±1 h around the window`, issued));

  const scenarioKnown = operatorCase.scenarios.length > 0 && !operatorCase.scenarios.includes('cause_unknown');
  const scenario = scenarioKnown ? null : inferScenario(operatorCase.originalText, forecast);
  // No scenariosSetAt: the table shows it as system inferred, not operator supplied.
  return { ...operatorCase, facts, ...(scenario ? { scenarios: [scenario], scenariosSetAt: undefined } : {}) };
}

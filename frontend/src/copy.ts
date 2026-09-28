// All scope labels and caveats live here so the national forecast and the
// TYTFS planning scenario are named the same way in every state, and so the
// smoke test can check that copy never overclaims.

export const COPY = {
  appTitle: 'Constraint outlook',
  appPhase: 'Prototype',
  appSubtitle: 'When national constraint risk rises, and what a planned outage could change in a planning model.',

  forecastTitle: 'National forecast',
  forecastKind: 'Statistical forecast',
  forecastScope: 'All-Ireland constraint MWh and event risk, 1–24 hours ahead',
  forecastCaveat:
    'Forecasts the national constraint total only, separate from system-wide curtailment. The labels it learns from are national totals, so it does not identify a line, wind farm, node or constraint group.',
  forecastLoading: 'Loading national forecast…',
  forecastError: 'National forecast could not be loaded.',
  contextTitle: 'Inputs available at decision time',

  scenarioTitle: 'TYTFS planning scenario',
  scenarioKind: 'Planning model',
  scenarioScope: 'Modelled intact vs planned-outage vs selected N-1 comparison on a 2024 planning case',
  scenarioCaveat:
    'DC flows from a Ten Year Transmission Forecast Statement (TYTFS) 2024 planning case, not the 2026 operating network. Loading and headroom are screening proxies, not measured or future operational flows. The selected N-1 run is one study case, not an operational security assessment.',
  scenarioLoading: 'Loading TYTFS planning scenario…',
  scenarioError: 'TYTFS planning scenario could not be loaded.',
  scenarioEmpty: 'Select a reviewed outage to see its modelled effect.',
  scenarioExcerpt: 'Showing the monitored branch only.',

  forecastConfidence: 'Forecast confidence',
  assetMatchConfidence: 'Asset match',

  notAvailable: 'Not available',
  fixtureBanner: 'Offline sample: scenario values copied from docs/NETWORK_SCENARIO_DEMO.md. Not served by the API yet.',
} as const;

// Phrases the UI must never show. Checked by the smoke test.
export const FORBIDDEN_PHRASES = [
  'will be constrained',
  'will constrain',
  'actual loading',
  'actual future loading',
  'guaranteed',
  'real-time flow',
  'binding line',
  'binding constraint group',
  'affected wind farm',
  'n-1 secure',
  'passes n-1',
  'fails n-1',
  'curtailment forecast',
  'avoided',
];

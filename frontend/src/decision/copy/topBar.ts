// Top bar copy (UI brief section 1). Plain operator language.

import type { ViewMode } from '../types';

export const TOP_BAR_COPY = {
  viewLegend: 'View',
  viewLabel: {
    national: 'National grid',
    precise: 'Precise grid',
    site: 'Site',
  } satisfies Record<ViewMode, string>,
  viewHint: {
    national: 'All-island conditions and affected groups.',
    precise: 'Browse named plants in the planning grid case.',
    site: 'Focus on one named plant.',
  } satisfies Record<ViewMode, string>,
  siteLabel: 'Plant',
  location: 'Location',
  allIsland: 'All-island',
  connection: 'Connection',
  limitingRoute: 'Limiting route',
  currentTime: 'Current time',
  window: 'Assessment window',
  dataStatus: 'Data status',
  source: 'Source',
  noAssessment: 'No assessment yet',
  noSite: 'No site selected',
  siteAllIslandNote: 'Plant names come from the ECP planning workbook. Connections and plant outcomes are not live or verified.',
  // A live feed without a full assessment keeps its own label and tone, so it
  // never carries the same badge as a fully assessed live result.
  liveFeed: 'Live feed',
};

// Top bar copy (UI brief section 1). Plain operator language.

import type { ViewMode } from '../types';

export const TOP_BAR_COPY = {
  viewLegend: 'View',
  viewLabel: {
    national: 'National grid',
    site: 'Precise grid / site',
  } satisfies Record<ViewMode, string>,
  viewHint: {
    national: 'All-island conditions and affected groups.',
    site: 'One site, its connection and the route that limits it.',
  } satisfies Record<ViewMode, string>,
  siteLabel: 'Site',
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
  siteAllIslandNote: 'All-island limits that affect this site still apply. The safety panel shows them.',
  // Live feed that the backend has not validated. Never the same as Live.
  liveNotValidated: 'Live — not validated',
};

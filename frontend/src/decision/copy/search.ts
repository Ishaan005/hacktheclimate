// Search bar copy (UI brief section 2). Plain operator language. Internal
// scenario IDs (T1–T4, H1–H4) never appear here.

export const SEARCH_COPY = {
  label: 'Find the situation',
  hint: 'Pick a suggested situation, or describe it in plain language. Enter finds a match. Shift+Enter adds a new line.',
  placeholder: 'For example: the route is safe now, but one trip would overload it',
  find: 'Find',
  suggestionsHeading: 'Suggested situations',
  addAnother: 'Add another limit',
  hideSuggestions: 'Hide suggestions',
  reviewHeading: 'What the app thinks is limiting',
  reviewHint: 'Check each limit before assessment. More than one limit can apply at once. Remove a limit that does not apply.',
  feedNote: 'Route, outage, timing and other details come from connected feeds such as SCADA. Check them in the situation table after assessment.',
  remove: 'Remove',
  removeLabel: (text: string) => `Remove: ${text}`,
  assess: 'Assess',
  assessing: 'Assessing…',
  causeUnknownHeading: 'Cause unknown',
  factsNeededLabel: 'Facts needed to find the cause',
  causeUnknownNext: 'Pick a suggested situation below, or add these facts to the description and search again.',
};

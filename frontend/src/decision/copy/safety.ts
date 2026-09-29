// Words for the safety panel (UI brief section 4). Plain operator language.

export const SAFETY_COPY = {
  title: 'Safety',
  overallLabel: 'Overall safety',
  familyChecksTitle: 'Constraint checks',
  familyMenuLabel: 'Show checks for',
  resultWord: { fail: 'fail', unknown: 'unknown', pass: 'pass' },
  noChecksShort: 'no checks',
  noFamilyChecks: 'No checks returned for this family. Treat it as Unknown.',
  noConditions: 'No limiting condition confirmed yet, so no family checks apply.',
  sharedReason: (count: number) => `${count} checks Unknown for the same reason:`,
  allIslandTitle: 'All-island limits that affect this decision',
  noAllIslandChecks: 'No all-island checks returned. Treat them as Unknown.',
  actionChecksTitle: 'Action-specific checks',
  actionChecksNote: 'Action checks add to the family checks. They never replace them.',
  noPlan: 'No plan selected. Action checks appear once a plan is chosen.',
  noStepChecks: 'No action checks returned for this step. Treat it as Unknown.',
  goNoGo: 'Go/no-go',
  step: 'Step',
  fields: {
    value: 'Value',
    limit: 'Limit',
    margin: 'Margin',
    worstTime: 'Worst time',
    worstFailure: 'Worst credible failure',
    source: 'Source',
  },
};

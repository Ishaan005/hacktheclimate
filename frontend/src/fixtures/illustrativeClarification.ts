// ILLUSTRATIVE follow-up questions for the offline solver and UI tests. One
// question of each kind, so the form can be checked without the LLM. Choice
// labels reuse words the illustrative scenarios match on.

import type { ClarificationRequest } from '../types';

export const illustrativeClarification: ClarificationRequest = {
  reason: 'The description does not name a limit or an area. Answer below to find the matching scenario.',
  questions: [
    {
      id: 'limit',
      kind: 'single_choice',
      prompt: 'Which limit is closest to binding?',
      helpText: null,
      required: true,
      options: [
        { value: 'thermal', label: 'Thermal overload' },
        { value: 'low_voltage', label: 'Low voltage' },
        { value: 'high_voltage', label: 'High voltage' },
        { value: 'snsp', label: 'SNSP' },
        { value: 'inertia', label: 'Inertia' },
        { value: 'surplus', label: 'Wind surplus' },
      ],
    },
    {
      id: 'area',
      kind: 'multi_choice',
      prompt: 'Which areas are affected?',
      helpText: 'Choose all that apply.',
      required: true,
      minSelected: 1,
      maxSelected: 3,
      options: [
        { value: 'west', label: 'West' },
        { value: 'north_west', label: 'North-west' },
        { value: 'south', label: 'South' },
        { value: 'south_east', label: 'South-east' },
        { value: 'dublin', label: 'Dublin' },
        { value: 'all_island', label: 'All-island' },
      ],
    },
    {
      id: 'lead_time',
      kind: 'number',
      prompt: 'How long until the interval starts?',
      helpText: 'Sets how soon the action must be achievable.',
      required: false,
      min: 0,
      max: 240,
      step: 15,
      unit: 'min',
      defaultValue: null,
    },
    {
      id: 'detail',
      kind: 'text',
      prompt: 'Anything else the solver should know?',
      helpText: 'For example an asset name or a planned outage.',
      required: false,
      placeholder: null,
      maxLength: 300,
    },
  ],
};

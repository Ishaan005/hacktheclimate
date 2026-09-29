// The real endpoint is the normal mode. Explicit fixture mode keeps the
// documented offline data available for development and UI tests.
export const USE_FIXTURE = import.meta.env.VITE_API_MODE === 'fixture' || import.meta.env.MODE === 'test';

// Send the description straight to the assistant (one model call) instead of
// running intake and showing the fact-review table first. Set
// VITE_CASE_REVIEW=on to bring the review step back. UI tests keep it on.
export const SKIP_CASE_REVIEW = import.meta.env.VITE_CASE_REVIEW !== 'on' && import.meta.env.MODE !== 'test';

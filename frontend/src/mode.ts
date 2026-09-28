// The real endpoint is the normal mode. Explicit fixture mode keeps the
// documented offline data available for development and UI tests.
export const USE_FIXTURE = import.meta.env.VITE_API_MODE === 'fixture' || import.meta.env.MODE === 'test';

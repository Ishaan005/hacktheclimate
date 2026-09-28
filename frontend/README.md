# Operator screen

Use a supported Node 22 release, then run the FastAPI server on
`127.0.0.1:8000` and start the UI:

```bash
npm ci
npm run dev
```

The UI calls `GET /v1/operator/view` by default. Vite proxies `/v1` to the
local API. That endpoint requires the TYTFS case import, reviewed generator
crosswalk and current 48 half-hour upstream input described in the
[network forecast guide](../docs/NETWORK_FORECAST_ARCHITECTURE.md). Missing
inputs show an unavailable state. The network panel shows model safety checks,
controlled action screens and the specific evidence still missing for a safe
recommendation.

For layout work without backend inputs, use the offline fixture explicitly:

```bash
VITE_API_MODE=fixture npm run dev
```

The fixture replays the documented 2024 Cashla planning case and leaves the
national forecast unavailable. It does not provide a real forecast or action.

Run `npm test`, `npm run lint`, and `npm run build` before changing the UI.

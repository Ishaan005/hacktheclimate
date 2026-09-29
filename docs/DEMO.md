# Golden-path demo

The demo is intentionally narrow. It uses a small synthetic four-bus planning
case packaged in the backend so a fresh clone can exercise the real DC solver,
action contract and bundle engine without the external TYTFS working files.

## Hero prompt

Paste this into the existing situation box:

> Planned outage in the west is causing a line overload. High wind around Ballylickey is constrained for the next 2 hours. What can we do to reduce dispatch-down?

The intake layer should extract:

- local network constraint
- planned outage exposure
- event window: next 2 hours
- affected area: West

After fact review, **Evaluate actions** runs the backend-owned golden path.

Expected story:

1. Baseline planned-outage export line is about **109.1% of rate A**.
2. 10 MW flexible demand alone captures renewable energy but does not relieve
   the export bottleneck.
3. 15 MW redispatch alone relieves the bottleneck but gets no renewable-capture
   credit.
4. The combined bundle reduces the modeled export line to about **81.8%** and
   has a **20 MWh modeled renewable-capture upper bound** over the two-hour
   window.
5. The UI labels it **Modeled candidate**, not a validated recommendation.
6. The 40 MWh → 20 MWh dispatch-down view is a **demo scenario assumption**
   using that capture upper bound, not a validated locational forecast.

## Refusal variant

Use:

> Planned outage in the west near Ballylickey plus another credible circuit loss creates an N-1 overload for the next 2 hours.

This resolves to T4. The additional synthetic circuit loss islands the West
demo area, so the action disappears and the UI explains why no modeled
candidate survives.

## Preflight

Run:

```bash
python -m scripts.check_demo_ready
```

It must end with:

```text
DEMO READY
```

## What is real vs synthetic

**Calculated live by project code**

- scenario/action contract eligibility
- action-bundle generation
- DC network flows
- planned-outage topology
- mixed flexible-demand + redispatch network effect
- thermal/islanding checks

**Synthetic demo inputs / assumptions**

- the four-bus operating case and asset names
- action availability/capability
- the national constraint numbers for the two-hour window
- treating the 20 MWh capture upper bound as the demo post-action
  dispatch-down reduction

Do not present this as the current Irish operating grid or as an operational
instruction. It is a planning-case demonstration of the product workflow.

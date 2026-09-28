# Designer's Guide: EirGrid MVP Frontend

## Purpose

This guide defines how the EirGrid MVP should look, behave, and communicate in the frontend.

It is intended to keep design decisions consistent across product, design, and engineering. The goal is a clean operational interface that supports fast operator decisions without looking like a finance dashboard, marketing site, or generic admin template.

## Design principles

### 1. Operational clarity first

The interface exists to help an operator understand:

- What is binding
- What action is recommended
- Whether it is feasible in time
- What the outcome becomes after the action

Every screen should support those four questions before adding explanation or decoration.

### 2. Security before value

Security is a gate, not a score.

The UI must always show post-action security status before net value, carbon value, or efficiency metrics. Do not visually imply that a profitable action is acceptable if it still breaches a guardrail.

### 3. Recommendation over exploration

This MVP is not a sandbox modelling environment.

The default experience should present one recommended action in a clear workflow. Assumptions, alternatives, evidence, and detailed metrics should be available, but secondary.

### 4. Calm, dense, readable

The product should feel composed and authoritative.

Use restrained colour, consistent spacing, strong typography, and obvious status handling. Avoid decorative gradients, over-illustration, excessive icon use, and visual noise.

## Product voice in UI

The interface language should be:

- Direct
- Operational
- Specific
- Neutral
- Evidence-based

Preferred style:

- “Generator A to 100 MW by 15:10”
- “Post-action result: within modelled limit”
- “Estimated avoided emissions”

Avoid:

- “Optimised outcome achieved”
- “Grid safe”
- “High-impact intervention”
- “Best action” without explanation

## Core interaction model

The main product interaction should use one collapsed scenario workspace:

**Scenario → Binding condition → Recommended action → New outcome**

Designers should preserve this structure in wireframes and high-fidelity screens.

### Default behaviour

The operator lands on a single scenario with the recommended action already selected.

Visible by default:

- Scenario context
- Binding condition
- Recommended action
- Baseline vs post-action comparison
- Primary metrics
- Guardrail status strip

Available on expansion:

- Assumptions
- Alternatives
- Evidence
- Cost details
- Carbon methodology

## Screen layout guidance

### Desktop layout

Primary target is operational desktop use.

Recommended structure:

- Left rail or top selector for scenario navigation
- Main content column for scenario workspace
- Optional right-side detail drawer for evidence and assumptions

The most important elements should remain above the fold:

- Binding condition
- Recommended action
- Post-action security result
- Avoided dispatch-down waste
- Net financial value

### Tablet and mobile layout

Responsive support is required, but mobile is secondary.

Rules:

- Stack comparison panels vertically
- Collapse secondary sections into accordions
- Keep the recommended action visible near the top
- Avoid wide dense tables where a card layout is clearer

## Interaction design rules

### Make actions feel actionable

Every recommendation must look like a real operator instruction.

Good:

- Includes asset name
- Includes location
- Includes current and target state
- Includes time window
- Includes status of executability

Bad:

- “Redispatch generator”
- “Apply voltage support”
- “Reduce renewables”

These are categories, not usable instructions.

### Use progressive disclosure

Default screens should be concise.

When more detail is required, reveal it through:

- Accordions
- Drawers
- Expandable cards
- Context panels

Do not send users through unnecessary page navigation for supporting detail.

### Always expose unknown honestly

If a guardrail or metric is unknown, show it as unknown.

Do not:

- Recolour it green
- Hide it by default
- Replace it with “clear” or “safe”
- Merge it into a positive overall state

### Comparison should be effortless

Baseline vs recommended-action comparison is the core product behaviour.

Design for side-by-side reading on desktop and quick vertical comparison on smaller screens. Labels, units, and metric order must stay identical between the two states.

## Design system foundation

The product should use a restrained, operational visual system.

### Design character

The interface should feel:

- Quiet
- Precise
- Stable
- Technical
- Trustworthy

It should not feel:

- Consumer-app playful
- Sales-oriented
- Overly futuristic
- Neon or “control room sci-fi”
- Generic SaaS template

## Colour system

Use semantic tokens, not raw colour names in components.

### Core principles

- Neutral surfaces carry most of the interface
- Colour is reserved for meaning and emphasis
- Status colours must be clear and consistent
- Accent colour should support focus, not dominate the screen

### Recommended colour tokens

#### Neutrals

```css
--color-bg: #F6F7F9;
--color-surface: #FFFFFF;
--color-surface-muted: #F1F3F6;
--color-surface-strong: #E7EBF0;
--color-border: #D6DCE5;
--color-border-strong: #B9C3D0;
--color-text: #15202B;
--color-text-muted: #51606F;
--color-text-faint: #6E7B88;
--color-text-inverse: #FFFFFF;
```

#### Brand / accent

Use a deep grid-blue accent for focus states, links, active selection, and key highlights.

```css
--color-accent: #0B4F8A;
--color-accent-hover: #083E6D;
--color-accent-soft: #DCEAF8;
--color-accent-strong: #083E6D;
```

#### Status tokens

```css
--color-success: #1F7A3E;
--color-success-soft: #E2F3E8;
--color-warning: #A66B00;
--color-warning-soft: #FFF2D9;
--color-danger: #B42318;
--color-danger-soft: #FEE4E2;
--color-info: #0B4F8A;
--color-info-soft: #DCEAF8;
```

#### Guardrail-specific semantics

```css
--color-status-within-limit: var(--color-success);
--color-status-breach: var(--color-danger);
--color-status-unknown: var(--color-warning);
```

### Colour usage rules

- Green only for `within_modelled_limit`
- Red only for `breach`
- Amber or neutral-warning only for `unknown`
- Do not invent extra status colours unless they represent real product meaning
- Avoid using multiple bright colours in one view unless there is a true status reason

### Chart and metric colour guidance

For compact charts or before/after visuals:

- Baseline: muted neutral or steel blue-grey
- Recommended action result: accent blue
- Positive delta: success green
- Negative delta or breach: danger red
- Unknown: warning amber or hashed neutral style

Avoid rainbow chart palettes.

## Typography

Typography should feel rigorous and legible at operational density.

### Font pairing

Use one primary sans-serif family for the entire interface.

Recommended stack:

```css
--font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--font-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
```

Use the sans-serif family for all interface copy, labels, headings, and cards.

Use the mono family only where it improves scanability:

- Timestamps
- MW / MWh technical values where alignment matters
- System IDs
- Dense table values

Do not use a display font. This is an operations product, not an editorial experience.

## Type scale

Use a tight, functional scale.

```css
--font-size-12: 0.75rem;   /* 12px */
--font-size-13: 0.8125rem; /* 13px */
--font-size-14: 0.875rem;  /* 14px */
--font-size-16: 1rem;      /* 16px */
--font-size-18: 1.125rem;  /* 18px */
--font-size-20: 1.25rem;   /* 20px */
--font-size-24: 1.5rem;    /* 24px */
--font-size-28: 1.75rem;   /* 28px */
```

### Type usage guidance

- 12px: compact metadata, secondary labels, chip text
- 13px: dense table text, supporting inline values
- 14px: default UI labels, buttons, tabs, field labels
- 16px: standard body copy and metric labels
- 18px: card headings, section headings
- 20px: panel titles
- 24px to 28px: top-level page or workspace heading only

Avoid huge hero-style typography.

### Font weights

```css
--font-weight-regular: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;
```

Usage:

- 400: body text
- 500: labels and values requiring slight emphasis
- 600: headings, metric values, status emphasis
- 700: very limited use, top-level heading only

Avoid overusing bold text across data-heavy screens.

### Line height

```css
--line-height-tight: 1.2;
--line-height-default: 1.4;
--line-height-relaxed: 1.6;
```

Use:

- 1.2 for compact numeric or metric displays
- 1.4 for interface text
- 1.6 only for longer help or documentation content

## Spacing system

Use a 4px base spacing scale.

```css
--space-2: 0.125rem;  /* 2px */
--space-4: 0.25rem;   /* 4px */
--space-8: 0.5rem;    /* 8px */
--space-12: 0.75rem;  /* 12px */
--space-16: 1rem;     /* 16px */
--space-20: 1.25rem;  /* 20px */
--space-24: 1.5rem;   /* 24px */
--space-32: 2rem;     /* 32px */
--space-40: 2.5rem;   /* 40px */
--space-48: 3rem;     /* 48px */
```

### Spacing rules

- Use 8 to 16px for spacing inside compact components
- Use 16 to 24px for card padding
- Use 24 to 32px between major panels
- Keep vertical rhythm regular and predictable
- Avoid mixed arbitrary spacing values

## Border radius and shadows

The UI should be crisp rather than soft and playful.

```css
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
```

Usage:

- 4px: chips, inputs, small pills
- 8px: cards, panels, dropdowns
- 12px: larger containers only where needed

Avoid overly rounded components.

### Shadows

Use shadows sparingly.

```css
--shadow-sm: 0 1px 2px rgba(16, 24, 40, 0.06);
--shadow-md: 0 4px 12px rgba(16, 24px, 40, 0.08);
```

Primary separation should come from surface, border, and spacing first. Shadows are secondary.

## Layout structure

### Page shell

Use a stable app-shell layout:

- Header or workspace bar
- Scenario navigation rail or selector
- Main content area
- Optional right-side detail or evidence area

### Panel behaviour

Panels should have clear boundaries and hierarchy.

Preferred panel anatomy:

- Title row
- Optional status chip or action link
- Primary content
- Secondary metadata
- Expand/collapse action where needed

### Grid usage

Recommended desktop rhythm:

- 12-column grid
- Main content spans 8 to 9 columns
- Supporting content spans 3 to 4 columns

Use consistent widths for cards inside the scenario workspace.

## Component guidance

### Buttons

Use a small button system.

#### Button types

- Primary: main confirm or focus action in a local context
- Secondary: less prominent action
- Tertiary / ghost: subtle action, often inside panels
- Destructive: only when removing or explicitly invalidating something

#### Button sizing

- Small: table actions, compact panels
- Medium: standard default
- Large: rare, only for key page-level actions

Do not place multiple equally prominent primary buttons in one panel.

### Chips and status tags

Use chips for concise state communication.

Examples:

- Within limit
- Breach
- Unknown
- Advisory
- Unconfirmed
- Executable now

Rules:

- Keep chips short
- Do not overload chips with long phrases
- Use icon plus text only when it improves scanability

### Tables

Tables should support scanning, not dominate the interface.

Rules:

- Right-align numeric columns where helpful
- Keep units consistent within columns
- Use zebra striping lightly, if at all
- Prefer compact headers and sticky column headings in longer tables
- Move verbose explanation out of tables and into detail panels

### Forms and controls

Forms should feel direct and technical.

Use:

- Clear labels above inputs
- Helper text only when needed
- Inline validation close to the control
- Logical unit suffixes for MW, MWh, EUR, tCO2e, and timestamps

Avoid placeholder text as the only label.

### Accordions and drawers

Use these for secondary detail, not the primary recommendation.

Good uses:

- Assumptions
- Engineering evidence
- Carbon methodology
- Alternative ranking reasons
- Cost breakdowns

## Content formatting rules

### Units and values

Always format technical values consistently.

Use standard display rules for:

- MW
- MWh
- EUR
- %
- tCO2e
- kV
- Mvar
- Timestamps

Example guidance:

- `100 MW`
- `78 MWh`
- `€12,400`
- `31.2 tCO2e`
- `220 kV`
- `+40 Mvar`
- `14:55`

Do not switch between inconsistent formats within the same screen.

### Numbers

Use tabular numerals in the frontend wherever values are compared vertically.

This is especially important for:

- Metric cards
- Tables
- Time values
- Cost values
- Before/after comparisons

### Labels

Keep labels short and literal.

Good:

- Post-action security result
- Earliest achievable execution
- Estimated avoided emissions

Bad:

- Security outlook
- Carbon opportunity score
- Time-to-execute confidence

## Accessibility and frontend practice

### Contrast

All status colours and text must meet accessible contrast requirements.

Do not rely on colour alone to communicate meaning. Pair colour with:

- Text labels
- Icons where helpful
- Position or grouping

### Keyboard behaviour

Interactive elements must be reachable and usable by keyboard.

Ensure proper behaviour for:

- Tabs
- Accordions
- Drawers
- Menus
- Table controls
- Filters

### Focus states

Every interactive element needs a clear visible focus state.

Use accent blue outlines or rings. Do not remove browser focus without a proper replacement.

### Hit areas

Clickable targets should be generous, especially for chips, row actions, and disclosure controls.

### Frontend implementation practice

Design should map cleanly into reusable frontend components.

Rules for interface design handoff:

- Use named tokens for colour, type, spacing, radius, and shadow
- Avoid one-off visual exceptions unless product meaning requires them
- Define component states explicitly: default, hover, active, focus, disabled, loading, error
- Define empty and unknown states at design time, not after development starts
- Design responsive behaviour intentionally rather than shrinking desktop layouts
- Keep labels, units, and ordering consistent across cards, tables, and drawers

## Suggested token starter set

```css
:root {
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;

  --font-size-12: 0.75rem;
  --font-size-13: 0.8125rem;
  --font-size-14: 0.875rem;
  --font-size-16: 1rem;
  --font-size-18: 1.125rem;
  --font-size-20: 1.25rem;
  --font-size-24: 1.5rem;
  --font-size-28: 1.75rem;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --line-height-tight: 1.2;
  --line-height-default: 1.4;
  --line-height-relaxed: 1.6;

  --space-2: 0.125rem;
  --space-4: 0.25rem;
  --space-8: 0.5rem;
  --space-12: 0.75rem;
  --space-16: 1rem;
  --space-20: 1.25rem;
  --space-24: 1.5rem;
  --space-32: 2rem;
  --space-40: 2.5rem;
  --space-48: 3rem;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  --shadow-sm: 0 1px 2px rgba(16, 24, 40, 0.06);
  --shadow-md: 0 4px 12px rgba(16, 24, 40, 0.08);

  --color-bg: #F6F7F9;
  --color-surface: #FFFFFF;
  --color-surface-muted: #F1F3F6;
  --color-surface-strong: #E7EBF0;
  --color-border: #D6DCE5;
  --color-border-strong: #B9C3D0;
  --color-text: #15202B;
  --color-text-muted: #51606F;
  --color-text-faint: #6E7B88;
  --color-text-inverse: #FFFFFF;

  --color-accent: #0B4F8A;
  --color-accent-hover: #083E6D;
  --color-accent-soft: #DCEAF8;
  --color-accent-strong: #083E6D;

  --color-success: #1F7A3E;
  --color-success-soft: #E2F3E8;
  --color-warning: #A66B00;
  --color-warning-soft: #FFF2D9;
  --color-danger: #B42318;
  --color-danger-soft: #FEE4E2;
  --color-info: #0B4F8A;
  --color-info-soft: #DCEAF8;

  --color-status-within-limit: var(--color-success);
  --color-status-breach: var(--color-danger);
  --color-status-unknown: var(--color-warning);
}
```

## Designer checklist

A screen is ready for frontend implementation when it has:

- Clear hierarchy of primary vs secondary information
- Defined grid and spacing behaviour
- Defined type scale usage
- Semantic colour usage
- All status states designed
- Empty, loading, unknown, and error states designed
- Component interaction states defined
- Responsive behaviour defined
- Consistent labels and unit formatting

## Final rule

When design choices conflict, choose the option that makes the recommendation easier to understand and the security state harder to misread.

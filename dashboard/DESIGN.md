---
name: Kinetic Sentinel
colors:
  surface: '#0e1416'
  surface-dim: '#0e1416'
  surface-bright: '#343a3c'
  surface-container-lowest: '#090f11'
  surface-container-low: '#171d1e'
  surface-container: '#1b2122'
  surface-container-high: '#252b2d'
  surface-container-highest: '#303638'
  on-surface: '#dee3e6'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#dee3e6'
  inverse-on-surface: '#2b3133'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#e79400'
  on-tertiary-container: '#563400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0e1416'
  on-background: '#dee3e6'
  surface-variant: '#303638'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  data-mono-lg:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: 0.05em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.1em
  helper-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  panel-gap: 12px
  stack-tight: 4px
  stack-md: 16px
---

## Brand & Style

This design system is engineered for mission-critical refinery safety analysis, where cognitive load management and rapid error detection are paramount. The aesthetic is rooted in **Industrial HUD (Heads-Up Display) Minimalism**, prioritizing high-density data visualization within a structured, low-distraction environment. 

The personality is authoritative, precise, and utilitarian. It utilizes a layered "Control Room" metaphor: a deep graphite base representing the physical environment, with steel-gray panels acting as active consoles. Subtle glows and high-chroma status indicators draw immediate attention to anomalies without causing visual fatigue during long shifts. The system avoids decorative elements, ensuring every pixel serves a functional diagnostic purpose.

## Colors

The palette is anchored by a dark-mode-only foundation to reduce eye strain in dimly lit control rooms.

- **Foundational Neutrals:** The base background is a deep Graphite (#121417), while Steel-Gray (#1e2126) is reserved for interactive panels and containers.
- **Status Indicators:** Color is used exclusively for semantic signaling. 
    - **Critical Risk (Red):** Used for emergency shutdowns, pipe pressure breaches, and immediate hazards.
    - **Warning (Amber):** Indicates threshold exceedance or maintenance requirements.
    - **Safe (Green):** Confirms active monitoring and nominal operations.
    - **System Info (Cyan):** The primary accent for interactive states, UI chrome, and telemetry data.

## Typography

Typography balances rapid legibility with technical precision. **Inter** provides high readability for labels and status messages, while **Geist** (a technical, developer-centric font) is used for all numerical data and telemetry to ensure tabular alignment and a "monospaced" engineering feel.

- **Headlines:** Reserved for module titles and equipment IDs.
- **Data Display:** Uses monospaced numerals to prevent layout shifting during real-time updates.
- **Labels:** Small-caps are utilized for static field descriptors to distinguish them from dynamic live data.

## Layout & Spacing

The layout employs a **Fluid-Density Grid**. While the overall container remains fluid to accommodate ultra-wide control room monitors, internal panels follow a strict 4px baseline grid.

- **High Density:** Padding within data tables and property panels is minimized to maximize the information visible above the fold.
- **Visual Grouping:** Use 12px gaps between primary modules (e.g., Boiler Map vs. Flow Metrics) to create clear mental boundaries.
- **Safe Margins:** A 24px outer margin ensures UI elements do not bleed into the bezel of industrial hardware displays.

## Elevation & Depth

This design system uses **Tonal Layering** and **Subtle Inner Glows** rather than traditional drop shadows to indicate hierarchy.

- **Level 0 (Base):** #121417 (The refinery floor).
- **Level 1 (Panels):** #1e2126 with a 1px stroke of #2d3139. This creates a "machined" look.
- **Level 2 (Popovers/Modals):** Same as Level 1 but with a subtle 8px ambient shadow and a 1px border of #334155 to lift it visually.
- **Active Indicators:** High-priority alerts utilize a soft outer glow (bloom effect) in the semantic color (Red/Amber) to simulate physical LED indicators on a control board.

## Shapes

The shape language is **Soft-Industrial**. 
- **Standard Radius:** 4px (Soft) is the system default for buttons, panels, and input fields. This maintains a professional, rigid feel while being more modern than sharp 90-degree corners.
- **Data Points:** Graph nodes and status pips use 0px (sharp) or 100% (pill) shapes to differentiate between structural UI and data markers.

## Components

- **Buttons:** Primary actions use a Cyan (#06b6d4) outline with a subtle background tint. Critical "E-Stop" buttons are solid Red (#ef4444) with white bold text.
- **Status Pips:** Small circular indicators that "pulse" slowly when a system is in a Warning state.
- **Input Fields:** Darker than the panel background (#121417) with a 1px border. The focus state uses a Cyan glow.
- **Cards/Modules:** Every card must have a header section with a 1px bottom separator and a label in `label-caps`.
- **Data Grids:** Zebra-striping is prohibited. Use thin 1px horizontal separators in #2d3139 to maintain vertical scanning speed.
- **Telemetry Gauges:** Circular or linear progress bars using a "segmented" look (divided into small blocks) to mimic vintage digital readouts.
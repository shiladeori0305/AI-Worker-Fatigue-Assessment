---
name: Industrial Sentinel
colors:
  surface: '#081425'
  surface-dim: '#081425'
  surface-bright: '#2f3a4c'
  surface-container-lowest: '#040e1f'
  surface-container-low: '#111c2d'
  surface-container: '#152031'
  surface-container-high: '#1f2a3c'
  surface-container-highest: '#2a3548'
  on-surface: '#d8e3fb'
  on-surface-variant: '#c6c6cd'
  inverse-surface: '#d8e3fb'
  inverse-on-surface: '#263143'
  outline: '#909097'
  outline-variant: '#45464d'
  surface-tint: '#bec6e0'
  primary: '#bec6e0'
  on-primary: '#283044'
  primary-container: '#0f172a'
  on-primary-container: '#798098'
  inverse-primary: '#565e74'
  secondary: '#90d0e1'
  on-secondary: '#003640'
  secondary-container: '#005664'
  on-secondary-container: '#89c9da'
  tertiary: '#dec29a'
  on-tertiary: '#3e2d11'
  tertiary-container: '#231500'
  on-tertiary-container: '#957d5a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#acedfe'
  secondary-fixed-dim: '#90d0e1'
  on-secondary-fixed: '#001f26'
  on-secondary-fixed-variant: '#004e5b'
  tertiary-fixed: '#fcdeb5'
  tertiary-fixed-dim: '#dec29a'
  on-tertiary-fixed: '#271901'
  on-tertiary-fixed-variant: '#574425'
  background: '#081425'
  on-background: '#d8e3fb'
  surface-variant: '#2a3548'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 24px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-max: 1440px
  gutter: 1.5rem
  margin-edge: 2rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

## Brand & Style

This design system is engineered for high-stakes industrial environments where cognitive load must be minimized and critical data must be immediately actionable. The brand personality is authoritative, resilient, and ultra-functional, reflecting the rugged nature of refinery operations.

The visual style is **Industrial Dark Mode with Subtle Glassmorphism**. It combines the structural reliability of a physical control room with the sophisticated data density of modern software. The aesthetic balances deep, matte surfaces with translucent "glass" overlays for secondary information, ensuring the most vital safety metrics appear to float and command attention. The emotional response is one of calm control and absolute clarity amidst complex mechanical processes.

## Colors

The palette is rooted in a **Deep Charcoal and Teal-inflected Slate** foundation to reduce eye strain in low-light control room settings. 

- **Primary & Neutral:** The background utilizes `#0F172A` (Deep Navy/Charcoal) to provide maximum contrast for data. Surfaces and containers use `#1E293B` to create a tiered hierarchy of information.
- **Safety Accents:** These are non-negotiable functional colors. 
    - **Emerald (#10B981):** Indicates nominal operations and safe zones.
    - **Amber (#F59E0B):** Used for warnings, maintenance requirements, and cautionary trends.
    - **Crimson (#EF4444):** Reserved exclusively for active alerts, gas leaks, or immediate life-safety hazards.
- **Data Visualization:** Use the new Secondary Teal-Slate `#2E7281` for technical secondary labels, trend lines, and inactive states to keep the interface decluttered with a professional, cool-toned precision.

## Typography

The design system utilizes **Inter** for its exceptional legibility and neutral, professional tone. It scales effectively from small status labels to large numerical displays.

- **Numerical Data:** For real-time sensor readings (PSI, Temperature, Gas Levels), use a monospaced font like JetBrains Mono or Inter's tabular font-feature settings to ensure numbers don't jump horizontally during updates.
- **Hierarchy:** Use `label-caps` for table headers and metadata to differentiate them clearly from primary data points.
- **Readability:** High contrast (White/Light Gray on Dark) is maintained throughout. Weights are kept at 400 for body and 600+ for headings to ensure "glow" from high-brightness monitors doesn't blur the text.

## Layout & Spacing

This design system follows a **12-column Bootstrap-compatible fluid grid**. The layout is designed to be "glanceable," with critical metrics positioned in the top-left quadrant or centered in large hero modules.

- **Grid:** 1.5rem (24px) gutters provide enough "breathing room" to prevent data density from becoming overwhelming.
- **Mobile/Tablet:** On smaller devices, the 12-column grid collapses to a single column. Information cards should reorder based on "Severity" rather than chronological order.
- **Density:** The dashboard uses a "Compact" spacing model. Vertical margins between related data points are kept tight (8px or 16px) to maximize the amount of information visible without scrolling.

## Elevation & Depth

To simulate a technical control panel, this design system uses **Tonal Layering and Glassmorphism** instead of traditional drop shadows.

- **Base Layer:** `#0F172A` (Background).
- **Surface Layer:** `#1E293B` with a subtle 1px border of `#334155` to define edges.
- **Overlay/Glass Layer:** Used for modals or floating HUD elements. Apply a `backdrop-filter: blur(12px)` with a semi-transparent background `rgba(30, 41, 59, 0.7)`.
- **Critical Focus:** Active alerts use a subtle outer glow (e.g., `0 0 15px rgba(239, 68, 68, 0.3)`) rather than a shadow, mimicking an illuminated physical LED indicator.

## Shapes

The shape language is **Soft (0.25rem)**, leaning towards a technical, machined look. 

- **Corners:** Avoid overly rounded or circular "consumer" aesthetics. Use 4px (0.25rem) radii for standard buttons and cards to maintain a precise, industrial feel. 
- **Status Indicators:** Use small squares or "pill" shapes for status badges, but keep the overall container structure rectangular.
- **Interactive Elements:** Buttons and inputs should have clearly defined, sharp boundaries to suggest a tactile "mechanical" toggle.

## Components

- **Buttons:** Primary buttons are solid Teal-Slate (`#2E7281`) with high-contrast white text. Danger/Alert buttons use a solid Red-600 background. All buttons feature a 1px inset border to simulate a "bezel" look.
- **Value Cards:** These are the core of the dashboard. They must feature a large `data-mono` value, a `label-caps` title, and a trend sparkline. The background color of the card should shift slightly when in a "Warning" or "Alert" state.
- **Status Chips:** Small, rectangular badges with a background opacity of 15% and a solid 1px border of the status color (Emerald, Amber, or Crimson).
- **Input Fields:** Darker than the surface layer (`#020617`), with a subtle 1px border. On focus, the border should glow with the Secondary color.
- **Alert List:** A vertical stack of high-contrast bars. Critical alerts should pulse slightly (opacity animation 0.8 to 1.0) to draw the eye immediately.
- **Gauges & Meters:** Use semi-circular or linear progress bars. The "fill" color should dynamically change from Emerald to Amber to Crimson as values cross safety thresholds.
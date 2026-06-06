---
name: Market Intelligence Dark
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
  tertiary: '#ffb3ad'
  on-tertiary: '#68000a'
  tertiary-container: '#ff817a'
  on-tertiary-container: '#7e000f'
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
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410004'
  on-tertiary-fixed-variant: '#930013'
  background: '#0e1416'
  on-background: '#dee3e6'
  surface-variant: '#303638'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  metric-xl:
    fontFamily: Geist
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
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
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-uppercase:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  caption:
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
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

This design system is engineered for professional data analysis within the Turkish ISP sector. The brand personality is authoritative, precise, and high-performance, prioritizing data density and rapid pattern recognition. 

The design style is **Modern Corporate Dark**, utilizing high-contrast surfaces to separate intelligence layers. It avoids decorative distractions in favor of a utilitarian, "glass-adjacent" aesthetic that emphasizes legibility. The emotional response should be one of control and clarity, providing analysts with a sophisticated environment to monitor volatile pricing and market shifts.

## Colors

The palette is strictly functional. The dark background (#0f172a) reduces eye strain during long analysis sessions, while the surface color (#1e293b) provides clear containment for data modules.

- **Primary Cyan (#06b6d4):** Used for neutral actions, information highlights, and primary brand touchpoints.
- **Success Green (#10b981):** Specifically reserved for price drops and positive market trends.
- **Critical Red (#ef4444):** Specifically reserved for price rises and negative churn indicators.
- **Typography:** Primary white-ish text provides maximum contrast against the dark background, with secondary and caption slates used to establish hierarchy and de-emphasize metadata.

## Typography

This system uses a dual-font strategy. **Geist** is employed for headings and high-impact numerical data (KPIs, percentages, pricing) to leverage its technical, precise character and excellent monospaced-like digit alignment. **Inter** is used for all UI labels, body copy, and secondary descriptions to ensure maximum readability and a neutral professional tone.

Numerical metrics should always use Geist with `tabular-nums` enabled where possible to ensure that fluctuating values do not cause layout shift.

## Layout & Spacing

The layout follows a **12-column fluid grid** for desktop and a **4-column fluid grid** for mobile. 

- **Density:** High. Margins and padding are kept tight to maximize the "above-the-fold" data visibility.
- **Rhythm:** An 8px base unit is used for component dimensions, while a 4px sub-unit is used for internal element spacing (e.g., icon to text).
- **Responsive Behavior:** On tablet/mobile, complex data tables should transition to a horizontal scroll or card-stack format. Sidebars collapse into a slim-rail or hamburger menu to prioritize the workspace.

## Elevation & Depth

This system avoids heavy shadows. Depth is communicated through **Tonal Layering** and **Low-Contrast Outlines**.

1.  **Background (#0f172a):** The furthest back layer.
2.  **Surface (#1e293b):** Card containers and navigation bars. These should feature a 1px subtle border (#334155) to define edges against the background.
3.  **Hover/Active States:** When an element is interacted with, its surface lightens slightly or gains a Cyan (#06b6d4) ghost-border.
4.  **Overlays:** Modals and tooltips use a slightly darker semi-transparent fill with a backdrop blur (8px) to maintain context without visual clutter.

## Shapes

The shape language is sharp and disciplined. We utilize **Small Radius (4px)** for most UI elements. This "Soft-Sharp" approach maintains a professional, engineering-focused look while avoiding the harshness of 90-degree corners.

- **Buttons/Inputs:** 4px (rounded-sm)
- **Cards/Containers:** 8px (rounded-lg)
- **Status Pills:** 100px (fully rounded) for distinct differentiation from clickable buttons.

## Components

- **Buttons:** Primary buttons use Cyan background with dark text (#0f172a) for maximum contrast. Secondary buttons are outlined with Cyan.
- **Data Tables:** Row headers use `#f1f5f9` (bold), and cells use `#cbd5e1`. Alternate row striping is not required; use 1px slate dividers instead.
- **Trend Indicators:** Price drops must feature the Green (#10b981) color with a downward arrow. Price rises must feature Red (#ef4444) with an upward arrow.
- **Input Fields:** Darker than the surface (#0f172a) with a 1px border (#334155). On focus, the border transitions to Cyan.
- **Cards:** Used as the primary unit for dashboard modules. Cards must include a header section with Geist-font labels and a body section for charts or Inter-font lists.
- **Charts:** Use a 2px stroke width for line charts. Use primary, secondary, and tertiary colors for data series. Grid lines within charts should be low-visibility (#334155).
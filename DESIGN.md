# Design System: Scouter

## 1. Visual Theme & Atmosphere

Scouter is a commercial intelligence cockpit — not a CRM, not a dashboard template. The interface communicates authority through restraint: a strictly monochromatic foundation of black, white, and grays. Color is reserved exclusively for functional semantics (status pipeline, quality badges, destructive actions). Every pixel earns its place by serving an operational purpose.

The aesthetic is data-forward and utilitarian. Monospace numerals for scores and budgets. Geometric headings that scan quickly. Generous whitespace that lets dense information breathe. The overall mood is a disciplined command center — serious enough for real business decisions, but with enough personality (through Mote's conversational AI layer) to feel alive rather than sterile.

The defining visual technique is **monochromatic structure with semantic color exceptions**: the entire UI — navigation, buttons, cards, charts, inputs — is achromatic (OKLCH with zero chroma). Color only appears in status badges, quality indicators, and destructive actions where it serves a functional scanning purpose. This creates maximum contrast and lets semantic colors command immediate attention.

**Key Characteristics:**
- Fully monochromatic UI — black, white, and grays only. No decorative color accents.
- Color reserved for functional semantics: status pipeline badges, quality badges (emerald/amber/red), destructive red
- High-contrast inverted buttons: `bg-foreground text-background` (black on white in light mode, white on black in dark mode)
- Three-font system: geometric display (Satoshi), humanist body (Geist Sans), tabular data (Geist Mono)
- Sidebar-driven layout with fixed left navigation and adaptive content area
- Rounded containers (`rounded-xl`) nested inside the viewport with subtle border treatment
- Dark mode as a first-class citizen, not an afterthought — uses transparent white borders and adjusted lightness values
- Status pipeline represented through a consistent 13-color semantic system (slate through green)
- Minimal shadow usage — depth communicated through border and background layering
- 4px base spacing with an 8px primary rhythm (Tailwind default scale)
- Spanish-language UI with Argentine conventions (`lang="es"`)

## 2. Color Palette & Roles

All colors are defined in the OKLCH color space for perceptual uniformity across light and dark modes. Approximate hex values are provided for quick reference.

### Foundation (Achromatic)

**Light Mode**

| Role | OKLCH | Approx. Hex | Usage |
|------|-------|-------------|-------|
| Background | `oklch(0.985 0 0)` | `#FAFAFA` | Page background behind the content shell |
| Foreground | `oklch(0.145 0 0)` | `#1A1A1A` | Primary text, headings |
| Card | `oklch(1 0 0)` | `#FFFFFF` | Card and container backgrounds |
| Primary | `oklch(0.205 0 0)` | `#2B2B2B` | Default button background, high-emphasis elements |
| Secondary | `oklch(0.97 0 0)` | `#F5F5F5` | Secondary button background, subtle fills |
| Muted | `oklch(0.97 0 0)` | `#F5F5F5` | Disabled backgrounds, inactive surfaces |
| Muted Foreground | `oklch(0.556 0 0)` | `#7C7C7C` | Placeholder text, secondary labels, timestamps |
| Accent | `oklch(0.97 0 0)` | `#F5F5F5` | Focus/hover backgrounds on menu items |
| Popover | `oklch(1 0 0)` | `#FFFFFF` | Dropdown and popover backgrounds |
| Border | `oklch(0.922 0 0)` | `#E5E5E5` | Card borders, dividers, input outlines |
| Ring | `oklch(0.708 0 0)` | `#A3A3A3` | Focus ring on interactive elements |

**Dark Mode**

| Role | OKLCH | Approx. Hex | Usage |
|------|-------|-------------|-------|
| Background | `oklch(0.145 0 0)` | `#1A1A1A` | Page background |
| Foreground | `oklch(0.985 0 0)` | `#FAFAFA` | Primary text |
| Card | `oklch(0.205 0 0)` | `#2B2B2B` | Card backgrounds |
| Primary | `oklch(0.922 0 0)` | `#E5E5E5` | Inverted primary — light on dark |
| Secondary | `oklch(0.269 0 0)` | `#383838` | Secondary fills |
| Muted | `oklch(0.269 0 0)` | `#383838` | Disabled backgrounds, inactive surfaces |
| Muted Foreground | `oklch(0.708 0 0)` | `#A3A3A3` | De-emphasized text |
| Accent | `oklch(0.269 0 0)` | `#383838` | Focus/hover backgrounds on menu items |
| Popover | `oklch(0.205 0 0)` | `#2B2B2B` | Dropdown and popover backgrounds |
| Border | `oklch(1 0 0 / 10%)` | `rgba(255,255,255,0.1)` | Transparent white borders |
| Input | `oklch(1 0 0 / 15%)` | `rgba(255,255,255,0.15)` | Input field borders (slightly more visible) |
| Ring | `oklch(0.556 0 0)` | `#7C7C7C` | Focus ring, adjusted for dark backgrounds |
| Destructive | `oklch(0.704 0.191 22.216)` | `#F87171` | Lighter red for dark mode legibility |

### Interactive Accent

There is no brand color. Interactive emphasis uses inverted foreground/background:

- **CTA buttons**: `bg-foreground text-background hover:bg-foreground/80` — black on white (light), white on black (dark).
- **Active nav (Mote)**: `bg-foreground text-background shadow-sm` (dark: `bg-foreground shadow-none`).
- **Active nav (other)**: `bg-muted text-foreground` (dark: `bg-white/10 text-white`).
- **Links**: `text-foreground/70 hover:text-foreground hover:underline` — subtle until hovered.
- **Focus rings**: `ring-ring/50` — gray ring, no color accent.

### Chart Colors (Grayscale Gradient)

Charts use a 5-step grayscale that adapts to the active mode for legibility:

**Light Mode**

| Token | OKLCH | Approx. Hex | Usage |
|-------|-------|-------------|-------|
| `--chart-1` | `oklch(0.70 0 0)` | `#A3A3A3` | Lightest data series |
| `--chart-2` | `oklch(0.55 0 0)` | `#737373` | Second data series |
| `--chart-3` | `oklch(0.40 0 0)` | `#525252` | Third data series |
| `--chart-4` | `oklch(0.25 0 0)` | `#333333` | Fourth data series |
| `--chart-5` | `oklch(0.15 0 0)` | `#1A1A1A` | Darkest data series |

**Dark Mode**

| Token | OKLCH | Approx. Hex | Usage |
|-------|-------|-------------|-------|
| `--chart-1` | `oklch(0.85 0 0)` | `#D4D4D4` | Lightest data series |
| `--chart-2` | `oklch(0.70 0 0)` | `#A3A3A3` | Second data series |
| `--chart-3` | `oklch(0.55 0 0)` | `#737373` | Third data series |
| `--chart-4` | `oklch(0.40 0 0)` | `#525252` | Fourth data series |
| `--chart-5` | `oklch(0.30 0 0)` | `#404040` | Darkest data series |

### Status Pipeline Colors

Each lead status maps to a Tailwind color with light/dark variants:

| Status | Color | Light BG | Light Text | Dark BG | Dark Text |
|--------|-------|----------|------------|---------|-----------|
| new | slate | `bg-slate-100` | `text-slate-700` | `bg-slate-800/50` | `text-slate-300` |
| enriched | blue | `bg-blue-50` | `text-blue-700` | `bg-blue-950/40` | `text-blue-300` |
| scored | indigo | `bg-indigo-50` | `text-indigo-700` | `bg-indigo-950/40` | `text-indigo-300` |
| qualified | violet | `bg-violet-50` | `text-violet-700` | `bg-violet-950/40` | `text-violet-300` |
| draft_ready | purple | `bg-purple-50` | `text-purple-700` | `bg-purple-950/40` | `text-purple-300` |
| approved | cyan | `bg-cyan-50` | `text-cyan-700` | `bg-cyan-950/40` | `text-cyan-300` |
| contacted | amber | `bg-amber-50` | `text-amber-700` | `bg-amber-950/40` | `text-amber-300` |
| opened | orange | `bg-orange-50` | `text-orange-700` | `bg-orange-950/40` | `text-orange-300` |
| replied | emerald | `bg-emerald-50` | `text-emerald-700` | `bg-emerald-950/40` | `text-emerald-300` |
| meeting | teal | `bg-teal-50` | `text-teal-700` | `bg-teal-950/40` | `text-teal-300` |
| won | green | `bg-green-100` | `text-green-700` | `bg-green-950/40` | `text-green-300` |
| lost | red | `bg-red-50` | `text-red-700` | `bg-red-950/40` | `text-red-300` |
| suppressed | gray | `bg-gray-100` | `text-gray-500` | `bg-gray-800/50` | `text-gray-400` |

### Quality & Score Colors

| Level | Condition | Color | Dot |
|-------|-----------|-------|-----|
| High | score >= 60 | emerald | `bg-emerald-500` |
| Medium | score >= 30 | amber | `bg-amber-500` |
| Low | score < 30 | red | `bg-red-500` |
| Unknown | — | slate | `bg-slate-400` |

### Scrollbar Colors

| Part | Light | Dark |
|------|-------|------|
| Track | `oklch(0.97 0 0)` | `oklch(0.18 0 0)` |
| Thumb | `oklch(0.82 0 0)` | `oklch(0.32 0 0)` |
| Thumb:hover | `oklch(0.65 0 0)` | `oklch(0.44 0 0)` |

## 3. Typography Rules

### Font Families

| Role | Font | Variable | Fallback Stack |
|------|------|----------|----------------|
| Headings | **Satoshi** (Variable) | `--font-heading` | `ui-sans-serif, system-ui, sans-serif` |
| Body / UI | **Geist Sans** (Variable) | `--font-geist-sans` → `--font-sans` | `ui-sans-serif, system-ui, sans-serif` |
| Data / Mono | **Geist Mono** (Variable) | `--font-geist-mono` → `--font-mono` | `ui-monospace, monospace` |

All fonts are loaded locally via `next/font/local` with `display: swap` for zero FOIT.

### Hierarchy

| Role | Font | Size | Weight | Tracking | Notes |
|------|------|------|--------|----------|-------|
| Page Title | Satoshi | `text-2xl` (24px) | `font-bold` (700) | `tracking-tight` | `.font-heading` class, page headers |
| Section Heading | Satoshi | `text-lg` (18px) | `font-semibold` (600) | normal | Card titles, section headers |
| Dialog Title | Satoshi | `text-base` (16px) | `font-medium` (500) | normal | Modal and dialog headings |
| Body | Geist Sans | `text-sm` (14px) | `font-normal` (400) | normal | Default UI text, descriptions |
| Small / Caption | Geist Sans | `text-xs` (12px) | `font-medium` (500) | normal | Labels, muted descriptions |
| Micro | Geist Sans | `text-[10px]` | `font-bold` (700) | normal | Model badges, sidebar version tags |
| Data Values | Geist Mono | `text-2xl` (24px) | `font-semibold` (600) | `tracking-tight` | Stat card primary values |
| Data Inline | Geist Mono | `text-xs` (12px) | `font-medium` (500) | normal | Scores, emails, dates in tables |
| Data Micro | Geist Mono | `text-[9px]` | `font-bold` (700) | normal | Model badge small variant |

### Principles

- **Three fonts, strict roles**: Satoshi for display and navigation labels, Geist Sans for UI, Geist Mono for data. Never cross these boundaries.
- **Tabular numerals always**: The `.font-data` utility enables `font-feature-settings: "tnum"` and `font-variant-numeric: tabular-nums` so columns of numbers align vertically.
- **Weight restraint**: Body text stays at 400-500. Only page titles reach 700. Bold (`font-bold`) in body text is reserved for `.font-data` micro labels.
- **Tracking-tight for impact**: Only `text-2xl` and above use `tracking-tight`. Smaller text uses default tracking.

## 4. Component Stylings

### Buttons

Built with `@base-ui/react/button` + CVA (class-variance-authority).

**Base classes** (all variants): `inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent text-sm font-medium whitespace-nowrap transition-all outline-none select-none active:translate-y-px`

| Variant | Background | Text | Hover | Border | Use |
|---------|-----------|------|-------|--------|-----|
| Default | `bg-primary` | `text-primary-foreground` | `bg-primary/80` | transparent | Primary actions (save, submit) |
| Outline | `bg-background` | inherited | `bg-muted` | `border-border` (dark: `border-input`) | Secondary actions, toggles |
| Secondary | `bg-secondary` | `text-secondary-foreground` | `bg-secondary/80` | transparent | Tertiary actions |
| Ghost | transparent | inherited | `bg-muted` | none | Toolbar actions, icon buttons |
| Destructive | `bg-destructive/10` | `text-destructive` | `bg-destructive/20` | transparent | Delete, remove actions |
| Link | transparent | `text-primary` | underline | none | Inline text links |

**Sizes:**

| Size | Height | Padding | Radius | Notes |
|------|--------|---------|--------|-------|
| default | `h-8` (32px) | `px-2.5` | `rounded-lg` | Standard |
| xs | `h-6` (24px) | `px-2` | `rounded-[min(var(--radius-md),10px)]` | Compact toolbars |
| sm | `h-7` (28px) | `px-2.5` | `rounded-[min(var(--radius-md),12px)]` | Inline actions |
| lg | `h-9` (36px) | `px-2.5` | `rounded-lg` | Emphasized actions |
| icon | `size-8` | — | `rounded-lg` | Icon-only standard |
| icon-xs | `size-6` | — | adaptive | Icon-only compact |
| icon-sm | `size-7` | — | adaptive | Icon-only small |
| icon-lg | `size-9` | — | `rounded-lg` | Icon-only large |

**Focus state** (all): `focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50`

### Cards & Containers

- **StatCard**: `rounded-2xl border border-border bg-card p-5 shadow-sm` with `hover:shadow-md` transition
- **Standard card**: `rounded-xl bg-background border border-border/40` (used by layout shell)
- **Icon box** (stat cards): `h-10 w-10 rounded-xl` with 13 color scheme variants (violet, emerald, amber, cyan, teal, green, blue, indigo, orange, purple, fuchsia, red + muted utility scheme). Each chromatic scheme uses: light `bg-COLOR-50` dark `bg-COLOR-950/30`, icon `text-COLOR-600` dark `text-COLOR-400`

### Badges

All badges share the base: `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium`

| Type | Additional Styles | Notes |
|------|-------------------|-------|
| StatusBadge | Dynamic `bg`/`text` from pipeline colors | 13 status variants |
| QualityBadge | `gap-1.5` + colored dot (`h-1.5 w-1.5 rounded-full`) | high/medium/low/unknown |
| ScoreBadge | `font-semibold font-data` | Uses score thresholds (60/30) |
| ModelBadge | `rounded font-bold font-data` (not `rounded-full`) | sm: `px-1 py-px text-[9px]`, md: `px-1.5 py-0.5 text-[10px]` |

### Inputs

Built with `@base-ui/react/input`.

- Height: `h-8` (32px)
- Padding: `px-2.5 py-1`
- Border: `border border-input`, dark: `dark:bg-input/30`
- Radius: `rounded-lg`
- Focus: `focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50`
- Disabled: `disabled:bg-input/50 dark:disabled:bg-input/80 disabled:opacity-50`
- Text: `text-base` on mobile, `md:text-sm` on desktop

### Dialogs

Built with `@base-ui/react/dialog`.

- Overlay: `bg-black/10` with `backdrop-blur-xs`
- Content: `rounded-xl bg-background p-4 ring-1 ring-foreground/10`
- Max width: `max-w-[calc(100%-2rem)]` mobile, `sm:max-w-sm` desktop
- Footer: `rounded-b-xl border-t bg-muted/50 p-4` with negative margins (`-mx-4 -mb-4`) to bleed into container edges
- Animation: `fade-in + zoom-in-95` on open, reverse on close at `duration-100`

### Tables

- Header: `h-10 px-2 font-medium whitespace-nowrap text-foreground`
- Cells: `p-2 whitespace-nowrap`
- Row hover: `hover:bg-muted/50`
- Selected row: `data-[state=selected]:bg-muted`
- Row borders: `border-b` (last child: no border)

### Dropdowns & Popovers

Built with `@base-ui/react/menu`.

- Container: `rounded-lg bg-popover p-1 shadow-md ring-1 ring-foreground/10`
- Items: `rounded-md px-1.5 py-1 text-sm` with `focus:bg-accent focus:text-accent-foreground`
- Labels: `px-1.5 py-1 text-xs font-medium text-muted-foreground`
- Separators: `-mx-1 my-1 h-px bg-border`
- Min width: `min-w-32`

### Tooltips

Built with `@base-ui/react/tooltip`.

- Content: `rounded-md bg-foreground px-3 py-1.5 text-xs text-background`
- Arrow: `size-2.5 rounded-[2px] bg-foreground`
- Side offset: `4px`
- Max width: `max-w-xs`

### Tabs

Built with `@base-ui/react/tabs`.

| Variant | List Style | Trigger Active State |
|---------|------------|---------------------|
| default | `bg-muted` pill container | `bg-background text-foreground` (dark: `border-input bg-input/30`) |
| line | `bg-transparent` no container | Same active styling, no background container |

- List: `rounded-lg p-[3px] h-8`
- Trigger: `rounded-md px-1.5 py-0.5 text-sm font-medium`
- Inactive text: `text-foreground/60` (dark: `text-muted-foreground`)

### Navigation

- **Sidebar width**: Expanded `w-52` (208px), Collapsed `w-[52px]` (52px)
- **Header**: `h-14` (56px) with logo and collapse toggle
- **Nav items (expanded)**: `rounded-xl py-2 px-3 gap-2.5 text-sm font-medium font-heading`
- **Nav items (collapsed)**: `rounded-xl py-2 px-[9px] gap-0` (icons centered, labels hidden)
- **Active (Mote)**: `bg-foreground text-background shadow-sm` (dark: `bg-foreground shadow-none`)
- **Active (other)**: `bg-muted dark:bg-white/10 text-foreground dark:text-white`
- **Inactive**: `text-muted-foreground hover:bg-muted hover:text-foreground`
- **Collapse transition**: `duration-[350ms] ease-in-out`
- **Icons**: lucide-react, `h-[18px] w-[18px]` (18px)

## 5. Layout Principles

### Spacing System

Base unit: **4px** (Tailwind default). Primary rhythm: **8px** increments.

Common spacing tokens used throughout the UI:

| Token | Value | Usage |
|-------|-------|-------|
| `gap-0.5` | 2px | Tight inline groups |
| `gap-1.5` | 6px | Button icon-to-text gaps |
| `gap-2` | 8px | Standard component spacing |
| `gap-3` | 12px | Section spacing within cards |
| `p-1` | 4px | Dropdown/popover internal padding |
| `p-2` | 8px | Table cell padding |
| `p-4` | 16px | Dialog padding, card internal sections |
| `p-5` | 20px | Stat card padding |
| `px-2.5` | 10px | Button horizontal padding, badge padding |
| `py-0.5` | 2px | Badge vertical padding |

### Grid & Container

- **Sidebar**: Fixed left, `w-52` expanded / `w-[52px]` collapsed
- **Content area**: Fixed right (`right-0`), with `pt-2 pr-2 pb-2` (8px inset from viewport edge)
- **Content container**: `rounded-xl border border-border/40 bg-background` — a rounded card that floats inside the viewport
- **Max content width**: No explicit max-width — content fills the available space minus sidebar
- **Page structure**: `<PageHeader>` at top (title + description + optional actions), then page body

### Whitespace Philosophy

- **Inset content model**: The main content area is inset 8px from the right/top/bottom viewport edges, creating a visual "floating panel" effect against the sidebar background color.
- **Card breathing room**: Stat cards use `p-5` (20px) for generous internal padding. Standard sections use `p-4` (16px).
- **Compact data density**: Tables and lists use tight `p-2` (8px) spacing to maximize data density without feeling cramped.

### Border Radius Scale

| Token | Multiplier | Computed | Usage |
|-------|-----------|----------|-------|
| `--radius-sm` | 0.6x | 6px | Small pills, compact elements |
| `--radius-md` | 0.8x | 8px | Dropdown items, small buttons |
| `--radius-lg` | 1.0x (base) | 10px | Standard — inputs, buttons, dropdowns |
| `--radius-xl` | 1.4x | 14px | Stat card icon boxes, content container |
| `--radius-2xl` | 1.8x | 18px | Stat cards |
| `--radius-3xl` | 2.2x | 22px | Reserved |
| `--radius-4xl` | 2.6x | 26px | Reserved |
| `rounded-full` | — | 9999px | Badges, avatar circles |

Base radius (`--radius`): `0.625rem` (10px).

## 6. Depth & Elevation

Scouter uses a deliberately minimal shadow system. Depth is primarily communicated through background color layering and border treatment, not shadows.

| Level | Treatment | Usage |
|-------|-----------|-------|
| Flat (L0) | No shadow | Default state for cards, containers, inputs |
| Subtle (L1) | `shadow-sm` | Active navigation item (Mote), stat cards at rest |
| Standard (L2) | `shadow-md` | Dropdowns, popovers, elevated menus |
| Map Popup (L3) | `0 8px 32px hsl(0 0% 0% / 0.12)` light / `hsl(0 0% 0% / 0.5)` dark | Map popups and overlays |
| Map Controls (L2.5) | `0 4px 16px hsl(0 0% 0% / 0.1)` light / `hsl(0 0% 0% / 0.4)` dark | Map zoom controls |
| Focus Ring | `ring-3 ring-ring/50` | All focusable interactive elements |

**Shadow Philosophy**: Shadows are an exception, not a system. The neutral OKLCH palette creates natural layering through lightness differences (card `1.0` sits above background `0.985` in light mode; card `0.205` above background `0.145` in dark mode). This makes explicit shadows unnecessary for most UI — they only appear on elements that truly float above the page (dropdowns, active nav items, map overlays).

**Border-as-depth**: The content shell uses `border border-border/40` (40% opacity border) to define its edge rather than a shadow. Dialogs use `ring-1 ring-foreground/10` (10% opacity ring). This is lighter than a shadow and creates a crisper boundary.

**Hover elevation**: Stat cards transition from `shadow-sm` to `shadow-md` on hover — the only place in the UI where interaction changes shadow depth.

## 7. Do's and Don'ts

### Do

- Use OKLCH for all custom color definitions — it ensures perceptual uniformity between light and dark modes.
- Apply `.font-data` (Geist Mono + tabular nums) to any column of numbers, scores, percentages, emails, or dates.
- Use `border border-border/40` for container edges instead of shadows — matches the existing content shell pattern.
- Follow the `bg-COLOR-50 dark:bg-COLOR-950/40` + `text-COLOR-700 dark:text-COLOR-300` pattern for new semantic badges.
- Use `rounded-lg` (10px) as the default radius for interactive elements (buttons, inputs, dropdowns).
- Use `rounded-xl` (14px) for container-level elements (content shell, stat card icon boxes).
- Use `rounded-2xl` (18px) for large cards (stat cards).
- Use `rounded-full` only for badges and avatar circles.
- Apply `active:translate-y-px` to clickable buttons for the subtle press-down micro-interaction.
- Keep dark mode borders as transparent white (`oklch(1 0 0 / 10%)`) rather than opaque gray values.
- Use the existing `StatCard` color schemes when adding new metric displays. The `violet` scheme now resolves to neutral (`bg-muted` / `text-foreground`). Prefer `muted` for new non-semantic cards.

### Don't

- Don't introduce decorative color accents (violet, blue, etc.). The UI is strictly monochromatic — color is reserved for semantic status badges and destructive actions only.
- Don't use `font-bold` (700) on body text — the maximum body weight is `font-semibold` (600), and only for data emphasis.
- Don't apply Satoshi (heading font) to body text or data. Don't apply Geist Sans to headings.
- Don't add `shadow-lg` or `shadow-xl` — the elevation system caps at `shadow-md` for UI elements.
- Don't use solid colored borders in dark mode (`border-gray-700` etc.) — use `oklch(1 0 0 / 10%)` transparent white.
- Don't add new Tailwind color scale stops to `globals.css` — use the existing OKLCH tokens via CSS variables.
- Don't use `text-black` or `text-white` directly — use `text-foreground`, `text-primary-foreground`, or `text-muted-foreground`.
- Don't use `rounded-none` or `rounded-sm` on interactive elements — the minimum for buttons/inputs is `rounded-lg` (10px).
- Don't create custom animation durations. Use `duration-100` (popups), `duration-200`/`duration-300` (standard), or `duration-[350ms]` (layout shifts) only.
- Don't add `hover:underline` to navigation items — hover state is `bg-muted`, not underline.
- Don't mix Radix UI primitives with Base UI — this project uses `@base-ui/react` exclusively.

## 8. Responsive Behavior

### Breakpoints

Scouter follows Tailwind's default breakpoint system:

| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | < 640px | Dialog: `max-w-[calc(100%-2rem)]`, Input text: `text-base` (16px to prevent iOS zoom), Dialog footer stacks vertically |
| sm (640px) | >= 640px | Dialog: `sm:max-w-sm`, Dialog footer: `sm:flex-row sm:justify-end` |
| md (768px) | >= 768px | Input text: `md:text-sm` (14px), some grid adjustments |
| lg (1024px) | >= 1024px | Standard desktop layout |

### Sidebar Collapse

The sidebar is the primary responsive mechanism:

- **Expanded** (`w-52` / 208px): Full labels visible, AI Activity section, version badge
- **Collapsed** (`w-[52px]` / 52px): Icons only, labels hidden via `overflow-hidden` + `opacity-0`
- **Transition**: `350ms ease-in-out` on width changes
- **State persistence**: `localStorage("scouter-sidebar-collapsed")` survives page reloads
- **Content area adapts**: Left offset shifts from `left-52` to `left-[52px]`

### Touch Targets

- Minimum interactive height: `h-8` (32px) for buttons and inputs
- Compact minimum: `h-6` (24px) for `xs` button variant
- Icon buttons: minimum `size-6` (24px × 24px)
- Navigation items: `h-8` (32px) with full-width click area

### Dark Mode

- Toggle: System / Light / Dark via `ThemeProvider` context
- Detection: Inline `<script>` in `<head>` reads `localStorage("scouter-theme")` before paint to prevent flash
- CSS: `.dark` class on `<html>`, `@custom-variant dark (&:is(.dark *))` for Tailwind v4
- All component variants define explicit dark mode overrides where needed

## 9. Agent Prompt Guide

### Quick Color Reference

| Role | Light | Dark |
|------|-------|------|
| Page BG | `oklch(0.985 0 0)` ~`#FAFAFA` | `oklch(0.145 0 0)` ~`#1A1A1A` |
| Text | `oklch(0.145 0 0)` ~`#1A1A1A` | `oklch(0.985 0 0)` ~`#FAFAFA` |
| Card BG | `oklch(1 0 0)` = `#FFF` | `oklch(0.205 0 0)` ~`#2B2B2B` |
| Border | `oklch(0.922 0 0)` ~`#E5E5E5` | `oklch(1 0 0 / 10%)` |
| Muted text | `oklch(0.556 0 0)` ~`#7C7C7C` | `oklch(0.708 0 0)` ~`#A3A3A3` |
| CTA / active | `bg-foreground` (inverted) | `bg-foreground` (inverted) |
| Destructive | `oklch(0.577 0.245 27.325)` | `oklch(0.704 0.191 22.216)` |

### Quick Font Reference

| Purpose | Class | Font |
|---------|-------|------|
| Page title | `font-heading text-2xl font-bold tracking-tight` | Satoshi |
| Section heading | `font-heading text-lg font-semibold` | Satoshi |
| Body text | `text-sm` (default) | Geist Sans |
| Muted label | `text-xs text-muted-foreground` | Geist Sans |
| Score / number | `font-data text-2xl font-semibold` | Geist Mono |
| Table data | `font-data text-xs` | Geist Mono |

### Example Component Prompts

**Stat card with icon:**
"Create a stat card with `rounded-2xl border border-border bg-card p-5 shadow-sm hover:shadow-md`. Include a `h-10 w-10 rounded-xl` icon box with `bg-muted dark:bg-muted`. Label in `text-sm font-medium text-muted-foreground`, value in `font-data text-2xl font-semibold tracking-tight text-foreground`."

**Status badge:**
"Create a badge with `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium`. For an 'enriched' status, use `bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300`."

**Page header:**
"Create a page header with title using `text-2xl font-bold tracking-tight text-foreground font-heading` and description as `text-sm text-muted-foreground`. Wrap in a flex container with `justify-between items-center`."

**Data table:**
"Create a table with header cells `h-10 px-2 font-medium whitespace-nowrap text-foreground` and body cells `p-2 whitespace-nowrap`. Rows get `border-b hover:bg-muted/50`. Apply `font-data` to numeric columns for tabular number alignment."

**Ghost icon button:**
"Create a ghost icon button with `size-8 rounded-lg` using the ghost variant: transparent background, `hover:bg-muted hover:text-foreground`, with a lucide-react icon at `size-4`."

### Iteration Guide

1. Always check both light and dark mode. If you defined a `bg-COLOR-50` make sure there's a `dark:bg-COLOR-950/40` counterpart.
2. Use `cn()` from `@/lib/utils` (clsx + tailwind-merge) for conditional class composition.
3. Test interactive states: default, hover, focus-visible, active, disabled. All five should be covered.
4. When adding a new semantic color, follow the established `bg-COLOR-50/text-COLOR-700` (light) + `bg-COLOR-950/40/text-COLOR-300` (dark) pattern.
5. Use `@base-ui/react` primitives for new interactive components — never raw HTML buttons or inputs.
6. Place new UI primitives in `dashboard/components/ui/`, shared components in `dashboard/components/shared/`, and feature components in `dashboard/components/{feature}/`.
7. Use `transition-all` with existing duration tokens. Avoid CSS `@keyframes` unless the animation is complex enough to justify it (prefer Tailwind's `animate-in`/`animate-out` data-attribute system).

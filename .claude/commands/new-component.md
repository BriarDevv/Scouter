Create a new React component for the ClawScout dashboard.

The user will provide: component name, purpose, and where it's used.

## Checklist

1. **Decide location** based on scope:
   - `components/ui/` — base primitives wrapping @base-ui/react
   - `components/shared/` — reusable across multiple pages
   - `components/dashboard/` — overview page widgets
   - `components/layout/` — page structure (sidebar, header)
   - `components/settings/` — settings page sections
   - `components/map/` — map-related components
   - `components/leads/` — leads-specific components

2. **Create the file** with kebab-case naming (e.g., `my-component.tsx`)

3. **Add "use client"** if the component has interactivity (state, effects, events)

4. **Use CVA** for variant-based styling:
   ```tsx
   import { cva, type VariantProps } from "class-variance-authority"
   ```

5. **Use cn()** for class merging:
   ```tsx
   import { cn } from "@/lib/utils"
   ```

## Conventions

- **UI library**: base-ui (NOT Radix) — use `render` prop, not `asChild`
- **Icons**: lucide-react
- **Animations**: framer-motion (for collapsible/expandable sections)
- **All text in Spanish (es-AR)**
- **Props interface**: Define inline or export from the same file
- **No default exports** — use named exports

## Patterns to follow

- Stat card: `components/shared/stat-card.tsx`
- Status badge: `components/shared/status-badge.tsx`
- Collapsible section: `components/shared/collapsible-section.tsx`
- Complex widget: `components/dashboard/control-center.tsx`

## After creation

Run `npx tsc --noEmit` from `dashboard/` to verify no type errors.

Create a new dashboard page for ClawScout.

The user will provide: page name, route, and purpose.

## Checklist

1. **Create the page file** at `dashboard/app/<route>/page.tsx`
2. **Add "use client"** at the top (all pages are client components)
3. **Use PageHeader** from `@/components/layout/page-header` for the heading
4. **Use the data hook** `usePageData` from `@/lib/hooks/use-page-data` for async data loading
5. **Add skeleton loading** using components from `@/components/shared/skeleton`
6. **Add empty state** using `EmptyState` from `@/components/shared/empty-state`
7. **Add to sidebar** in `dashboard/components/layout/sidebar.tsx` — add to `NAV_ITEMS` or `EXTRA_NAV_ITEMS`
8. **Add API functions** if needed in `dashboard/lib/api/client.ts`
9. **Add types** if needed in `dashboard/types/index.ts`

## Conventions

- All text in **Spanish (es-AR)** — labels, headings, empty states, everything
- Use `lucide-react` for icons
- Use `@/lib/formatters` for date/number formatting (es-AR locale)
- Use `@/lib/constants` for status/quality/signal color configs
- Tailwind v4 — use existing theme tokens from `globals.css`
- No `tailwind.config.ts` — all theming is inline via `@theme`

## Patterns to follow

Look at existing pages for reference:
- Simple table page: `app/suppression/page.tsx`
- Complex page with charts: `app/performance/page.tsx`
- Page with tabs: `app/settings/page.tsx`
- Page with real-time data: `app/activity/page.tsx`

## After creation

Run `npx tsc --noEmit` from `dashboard/` to verify no type errors.

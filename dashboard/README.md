# Scouter Dashboard

Next.js 16 App Router frontend for the Scouter lead prospecting system.

**Stack:** TypeScript (strict), Tailwind CSS v4, shadcn/ui (base-ui), recharts, lucide-react.

## Quick Start

```bash
cd dashboard
npm install
npm run dev          # http://localhost:3000
npx tsc --noEmit     # Type check
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Mote chat (main page) |
| `/panel` | Dashboard overview — stats, pipeline, AI health |
| `/leads` | Lead table with filters and search |
| `/leads/[id]` | Lead detail — signals, score, AI decisions, Scout findings |
| `/ai-office` | AI team dashboard — agents, decisions, investigations, outcomes |
| `/onboarding` | First-run setup wizard |
| `/outreach` | Draft management |
| `/performance` | Analytics by industry, city, source |
| `/settings` | Configuration — brand, credentials, channels, rules |
| `/responses` | Inbound reply classification |
| `/notifications` | System notifications |

## Structure

```
app/                    Pages (App Router)
  api/proxy/[...path]/  Server-side API proxy (hides API_KEY from browser)
  api/system/health/    Health check proxy
components/
  charts/               Recharts wrappers
  chat/                 Mote chat UI
  dashboard/            AI health card, top corrections, stats
  layout/               Sidebar, shell, readiness-gate, page-header
  leads/                AI decisions panel, investigation thread view
  settings/             All settings sections (brand, WhatsApp, Telegram, etc.)
  shared/               Reusable primitives (empty-state, stat-card, badges)
  ui/                   shadcn/ui base components
lib/
  api/client.ts         All backend API functions via apiFetch()
  constants.ts          Status configs, API_BASE_URL, score thresholds
  hooks/                use-chat, use-chat-panel
types/
  index.ts              All TypeScript interfaces
```

## Key Files for AI Agents

| File | Purpose |
|------|---------|
| `lib/api/client.ts` | `apiFetch()` helper + barrel re-export of 12 domain modules (`lib/api/leads.ts`, `lib/api/outreach.ts`, `lib/api/pipeline.ts`, etc.). Browser calls use `/api/proxy`, SSR uses the direct backend URL. Import from `@/lib/api/client` in either case — the barrel resolves to the right domain module. |
| `types/index.ts` | All shared TypeScript interfaces (~800 lines) |
| `lib/constants.ts` | Status/quality/signal configs, score thresholds |
| `components/layout/readiness-gate.tsx` | Gates dashboard behind onboarding |
| `app/layout.tsx` | Root layout with theme, sidebar, readiness gate |

## API Proxy

All browser API calls route through `/api/proxy/[...path]`:
- Injects `API_KEY` server-side (never exposed to browser)
- Path allowlist prevents SSRF (23 allowed prefixes)
- `API_BASE_URL` = `/api/proxy` in browser, direct backend URL in SSR

## Tailwind CSS v4

- `@theme inline` in `app/globals.css` for design variables
- **No `tailwind.config.ts`** — all configuration is inline
- PostCSS via `postcss.config.mjs` with `@tailwindcss/postcss`

## Component Library

Uses **shadcn/ui 4.x with the `base-nova` style preset**, which ships `@base-ui/react` primitives instead of Radix:

- `components.json` declares `"style": "base-nova"` (not the default `"default"` or `"new-york"`). Do not change this — it selects the base-ui primitive family.
- `@base-ui/react` is the only primitive library. Do NOT add `@radix-ui/*` packages.
- Use the `render` prop instead of `asChild` for composition — this is a base-ui convention.
- `app/globals.css` imports `shadcn/tailwind.css` (a stylesheet shipped by the `shadcn` npm package) to pull in the base-nova token bundle and `tw-animate-css` data-attribute animations. Keep the import — removing it breaks `data-open:animate-in` on every primitive.
- Base components in `components/ui/`. Add new primitives there.
- Shared dashboard components (stat-card, status-badge, model-badge, empty-state) in `components/shared/`.
- Feature-specific components in `components/{feature}/` (leads, outreach, dashboard, chat, map, ...).

See `DESIGN.md` for the complete visual contract, including the 4 declared exceptions in § 9 (maps, toasts, animations, minor semantic exceptions).

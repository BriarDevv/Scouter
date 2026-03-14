# ClawScout Dashboard

Panel de control SaaS para el sistema de prospeccion ClawScout.
Construido con **Next.js 16** (App Router), **TypeScript**, **Tailwind CSS v4**, **shadcn/ui** (base-ui), **recharts** y **lucide-react**.

## Setup

```bash
# Instalar dependencias
npm ci

# Servidor de desarrollo (puerto 3000)
npm run dev
```

Abri [http://localhost:3000](http://localhost:3000) en tu navegador.

## Variables de entorno

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | URL base de la API |
| `NEXT_PUBLIC_USE_REAL_API` | `true` | `false` para usar datos mock locales |

El toggle vive en `lib/api/client.ts`. Cuando `NEXT_PUBLIC_USE_REAL_API` es `"false"`, el cliente devuelve datos mock desde `data/mock.ts` sin tocar el backend.

## Paginas

| Ruta | Descripcion |
|------|-------------|
| `/` | **Overview** -- metricas generales, pipeline, graficos temporales |
| `/leads` | **Leads** -- tabla paginada con filtros y busqueda |
| `/leads/[id]` | **Lead Detail** -- senales, score, drafts, timeline |
| `/outreach` | **Outreach** -- drafts pendientes, aprobados, enviados |
| `/performance` | **Performance** -- metricas por industria, ciudad, fuente |
| `/suppression` | **Suppression** -- lista de supresion global |
| `/responses` | **Responses** -- respuestas inbound clasificadas |
| `/activity` | **Activity** -- log de actividad del sistema |
| `/notifications` | **Notifications** -- notificaciones y alertas |
| `/security` | **Security** -- configuracion de seguridad |
| `/settings` | **Settings** -- configuracion general del sistema |

## Notas sobre la libreria de componentes

Este proyecto usa **shadcn/ui con base-ui (NO Radix)**. La diferencia clave:

- Usar la prop `render` en vez de `asChild` para composicion de componentes.
- Los componentes base viven en `components/ui/`.
- Componentes compartidos del dashboard en `components/shared/` (StatCard, StatusBadge, QualityBadge, ScoreBadge, EmptyState, PageHeader).

## Tailwind CSS v4

- Se usa `@theme inline` en `app/globals.css` para definir variables de diseno.
- **No existe `tailwind.config.ts`** -- toda la configuracion esta inline.
- PostCSS se configura en `postcss.config.mjs` con `@tailwindcss/postcss`.

## Estructura

```
dashboard/
+-- app/                  # App Router -- paginas y layouts
|   +-- layout.tsx        # Layout raiz con providers
|   +-- page.tsx          # Overview / home
|   +-- leads/            # Leads y detalle
|   +-- outreach/         # Gestion de drafts
|   +-- performance/      # Metricas de rendimiento
|   +-- suppression/      # Lista de supresion
|   +-- responses/        # Respuestas inbound
|   +-- activity/         # Log de actividad
|   +-- notifications/    # Notificaciones
|   +-- security/         # Seguridad
|   +-- settings/         # Configuracion
+-- components/
|   +-- ui/               # shadcn/ui base components
|   +-- shared/           # Componentes reutilizables
|   +-- charts/           # Graficos (recharts)
|   +-- dashboard/        # Widgets del dashboard
|   +-- layout/           # Sidebar, header, navigation
|   +-- leads/            # Componentes de leads
|   +-- providers/        # Context providers
|   +-- settings/         # Componentes de settings
+-- data/                 # Mock data para desarrollo
+-- lib/
|   +-- api/              # Cliente API + mock fallback
|   +-- hooks/            # Custom hooks
|   +-- constants.ts      # Configuracion de estados, colores, umbrales
|   +-- formatters.ts     # Utilidades de formato
|   +-- utils.ts          # Utilidades generales
+-- types/                # TypeScript type definitions
+-- public/               # Assets estaticos
```

## Scripts

| Comando | Descripcion |
|---------|-------------|
| `npm run dev` | Servidor de desarrollo (puerto 3000) |
| `npm run build` | Build de produccion |
| `npm run start` | Servidor de produccion |
| `npm run lint` | ESLint |

## Type checking

```bash
npx tsc --noEmit
```

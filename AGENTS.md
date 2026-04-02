# ClawScout

Private lead prospecting system for web development services.
Python 3.12+ / FastAPI backend, Next.js 16 frontend, Mote agent system.

## Architecture

```
app/                        Python backend (FastAPI)
  agent/                    Mote agentic chat (SSE streaming, 55 tools)
    core.py                   Agent loop: run_agent_turn() streams LLM + executes tools
    hermes_format.py          Parses <tool_call> XML from Hermes 3 models
    channel_router.py         Routes agent to Telegram / WhatsApp channels
    prompts.py                Builds system prompt from SOUL.md + IDENTITY.md
    tools/                    15 tool modules organized by domain
      leads.py                  search, detail, count, create, update status
      stats.py                  dashboard stats, pipeline, industry, city, source, time series
      pipeline.py               run pipeline, batch pipeline, status
      outreach.py               drafts, approve, reject, send, logs, WhatsApp
      mail.py                   sync inbound, list, classify
      replies.py                generate/send reply drafts
      reviews.py                review lead, review draft
      research.py               dossier, brief, research, export (NEW)
      territories.py            CRUD territories
      crawl.py                  start/status territory crawls
      suppression.py            manage suppression list
      notifications.py          list, mark read, counts
      leader.py                 system overview, top leads, activity, replies
      settings.py               get/update operational settings
      system.py                 health check, current time
  api/v1/                   REST endpoints
    leads.py                  CRUD + export (CSV/JSON/XLSX) + research
    briefs.py                 Commercial brief CRUD (NEW)
    chat.py                   SSE streaming conversations
    crawl.py                  Territory crawl management
    outreach.py               Draft generation, approval, send
    mail.py                   Inbound mail sync + classification
    replies.py                Reply assistant drafts
    reviews.py                Reviewer second opinions
    dashboard.py              Stats aggregations
    performance.py            Analytics breakdown
    settings.py               Operational settings + runtime modes
    notifications.py          Notification management
    pipelines.py              Pipeline run tracking + batch
    tasks.py                  Task status + revoke
    territories.py            Territory CRUD
    suppression.py            Suppression list
    whatsapp.py               WhatsApp webhook
    telegram.py               Telegram webhook
    leader.py                 Leader overview endpoints
  core/                     Config (Pydantic Settings), crypto (Fernet), structlog logging
  crawlers/                 Google Maps crawler (base_crawler + google_maps_crawler)
  db/                       SQLAlchemy engine/session (sync, get_session dependency)
  llm/                      LLM client with role-based routing + sanitizer
    catalog.py                Model catalog and aliases
    resolver.py               Role -> model resolution
    client.py                 12 LLM functions (summarize, evaluate, draft, review, classify, dossier, brief)
    prompts.py                Prompt templates with <external_data> injection defense
    sanitizer.py              Input sanitization (HTML strip, injection pattern removal) (NEW)
  mail/                     SMTP send + IMAP ingest providers
  models/                   SQLAlchemy ORM (UUID PKs, all exported in __init__.py)
    lead.py                   Lead + LeadStatus + LeadQuality
    lead_signal.py            LeadSignal + SignalType (with confidence + source)
    lead_source.py            LeadSource
    research_report.py        LeadResearchReport + ResearchStatus + ConfidenceLevel (NEW)
    commercial_brief.py       CommercialBrief + 6 enums (budget, scope, contact, etc.) (NEW)
    artifact.py               Artifact + ArtifactType (NEW)
    outreach.py               OutreachDraft + OutreachLog
    outreach_delivery.py      OutreachDelivery (with partial unique index)
    conversation.py           Conversation + Message + ToolCall
    inbound_mail.py           EmailThread + InboundMessage + InboundMailSyncRun
    reply_assistant.py        ReplyAssistantDraft + ReplyAssistantReview
    reply_assistant_send.py   ReplyAssistantSend
    settings.py               OperationalSettings (singleton, 30+ toggles + runtime_mode)
    notification.py           Notification
    territory.py              Territory
    suppression.py            SuppressionEntry
    task_tracking.py          PipelineRun + TaskRun
    mail_credentials.py       MailCredentials (Fernet encrypted)
    whatsapp_credentials.py   WhatsAppCredentials
    telegram_credentials.py   TelegramCredentials
    whatsapp_audit.py         WhatsAppAuditLog
    telegram_audit.py         TelegramAuditLog
  outreach/                 Outreach message generator (with brief-conditioned drafts)
  schemas/                  Pydantic v2 schemas (XxxCreate / XxxUpdate / XxxResponse)
  scoring/                  Lead scoring engine (signals + industry + completeness + Google Maps)
  services/                 Stateless business logic (fn(db: Session, ...) pattern)
    research_service.py       Web research: website analysis, signal detection (NEW)
    brief_service.py          Commercial brief generation with pricing matrix (NEW)
    export_service.py         CSV/JSON/XLSX export (NEW)
    storage_service.py        Local file storage abstraction (NEW)
    + 20 other services (leads, outreach, mail, notifications, etc.)
  workers/                  Celery app, async tasks, janitor cleanup
    tasks.py                  Pipeline tasks (enrich, score, analyze, draft, research, review)
    brief_tasks.py            Brief generation + review tasks (NEW)
    celery_app.py             6 queues: enrichment, scoring, llm, reviewer, research, default
    janitor.py                Stale task sweep (every 5min)

dashboard/                  Next.js 16 frontend (App Router, TypeScript strict)
  app/                      15 pages
    page.tsx                  / — Mote chat (full-page)
    panel/                    /panel — operational dashboard
    leads/                    /leads — lead list + /leads/[id] detail (with dossier + brief)
    dossiers/                 /dossiers — HIGH lead dossier candidates (NEW)
    briefs/                   /briefs — commercial briefs list (NEW)
    outreach/                 /outreach — draft management
    responses/                /responses — inbound mail
    performance/              /performance — analytics
    map/                      /map — Leaflet map + territories
    suppression/              /suppression — suppression list
    notifications/            /notifications — notification center
    security/                 /security — security alerts
    settings/                 /settings — 11-tab config
    activity/                 /activity — real-time task monitor
  components/               UI organized by domain
    ui/                       shadcn/ui primitives (base-ui, NOT Radix)
    dashboard/                StatsGrid, ControlCenter (with runtime mode selector), PipelineFunnel
    chat/                     ChatPanel, ChatMessages, ChatInput, ToolCallCard
    leads/                    LeadsTable
    map/                      LeadMap, TerritoryPanel, HeatmapLayer
    settings/                 11 section components
    layout/                   Sidebar, LayoutShell, ThemeToggle, ActivityPulse
    shared/                   StatCard, StatusBadge, CollapsibleSection, ReplyDraftPanel
  lib/api/client.ts         Centralized API client (~75 functions)
  lib/hooks/                Custom hooks (usePageData, useChatPanel, useChat, useSystemHealth)
  types/index.ts            All TypeScript interfaces (Lead, Brief, Research, etc.)

tests/                      Pytest suite (SQLite override in conftest.py, 187 tests)
alembic/                    DB migrations (32 total)
infra/docker/               Dockerfile + .dockerignore
docs/                       Audits, roadmaps, specs, propuesta de negocio
```

## LLM Roles

| Role | Default Model | Purpose |
|------|--------------|---------|
| LEADER | qwen3.5:4b | Orchestration, summaries, briefs |
| EXECUTOR | qwen3.5:9b | Classification, draft generation, scoring, dossier, brief |
| REVIEWER | qwen3.5:27b | Quality review, brief review, second opinions (async) |
| AGENT | hermes3:8b | Mote chat agent — the leader |

## Pipeline (HIGH leads)

```
Lead ingestion (Google Maps crawler)
  -> Dedup (SHA-256)
  -> Enrichment (httpx website analysis, email extraction, signals)
  -> Scoring (rules-based, 0-100)
  -> LLM Analysis (Qwen 9B: summary + quality evaluation)
  -> IF quality == HIGH:
       -> Research (website deep analysis, metadata, signals)
       -> Dossier generation (LLM structured report)
       -> Commercial Brief (budget, opportunity, contact recommendation)
       -> Brief Review (REVIEWER 27B validation)
  -> Draft Generation (email + WhatsApp, conditioned on brief)
  -> Human Approval -> Send
```

## Runtime Modes

| Mode | Behavior |
|------|----------|
| **safe** | Everything requires manual approval. No auto-processing. |
| **assisted** | Pipeline runs automatically. Drafts generated. Send requires approval. |
| **auto** | Full automation including send. Use with caution. |

## Key Files

| File | Why it matters |
|------|---------------|
| `SOUL.md` | Mote personality — read by `app/agent/prompts.py` at startup |
| `IDENTITY.md` | Mote identity — same |
| `app/agent/core.py` | The Mote agent loop — SSE streaming + tool execution |
| `app/api/v1/` | All REST endpoints — start here for API changes |
| `app/services/` | All business logic — stateless, takes `db: Session` |
| `app/models/__init__.py` | Model registry — new models must be exported here |
| `dashboard/lib/api/client.ts` | Single API client — all frontend calls go through here |
| `tests/conftest.py` | Test DB setup (SQLite override) |
| `Makefile` | `make up`, `make down`, `make status` |

## Conventions

**Backend**: Ruff linter (line 100), structlog (event name + kwargs, no f-strings), services are stateless functions, UUID primary keys, enum values lowercase strings. LLM input sanitized via `app/llm/sanitizer.py`.

**Frontend**: Tailwind v4 (`@import "tailwindcss"`), CVA for variants, `cn()` utility, all text in Spanish (es-AR), kebab-case filenames, `"use client"` for interactive components.

**Both**: Dedup hash = SHA-256(business_name + city + domain). No auto-send in safe mode — all outreach requires human approval.

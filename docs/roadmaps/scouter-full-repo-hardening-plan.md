# Scouter Full Repo Hardening Plan — Post Re-Audit

**Date:** 2026-04-04 (v2 — after 31-commit hardening + re-audit)
**Source:** [scouter-full-repo-deep-audit.md](../audits/scouter-full-repo-deep-audit.md)
**Current score:** 8.5/10 → **Target: 9.5/10**

---

## What Was Already Done (Phases 0-4 v1)

- ✅ Pydantic schema gap fixed (runtime_mode, pricing_matrix)
- ✅ Suppression OR logic fixed
- ✅ Dynamic Tailwind classes replaced with static maps
- ✅ SSE JSON.parse wrapped in try/catch
- ✅ usePageData stale closure fixed
- ✅ deps.py deleted, get_db imported directly (28 routers)
- ✅ Shared task-utils.ts and ModelBadge extracted
- ✅ LayoutShell double nesting removed
- ✅ Tool registry caches inspect.signature at registration
- ✅ Pipeline orphan detection in janitor
- ✅ Singleton CheckConstraint on OperationalSettings
- ✅ Streaming export with yield_per
- ✅ Leads pagination + lightweight /leads/names endpoint
- ✅ ReadinessGate caches after unlock
- ✅ Type safety improvements (no as any, Record<string, unknown>)
- ✅ Tests migrated to PostgreSQL via testcontainers
- ✅ Alembic migration chain test
- ✅ PostgreSQL guardrail test
- ✅ 16 new tests (315 total)
- ✅ Architecture audit and docs updated
- ✅ .editorconfig, loading.tsx skeletons, error logging

---

## Phase 0 — Quick Wins (1-2 hours)

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 0.1 | Add null check before `message.lead_id` in review_tasks | HIGH | 5 min | `app/workers/review_tasks.py:238,168` |
| 0.2 | Add null guard before `res.body!.getReader()` in use-chat | HIGH | 5 min | `dashboard/lib/hooks/use-chat.ts:74` |
| 0.3 | Replace `batch!` with proper narrowing in activity-pulse | HIGH | 15 min | `dashboard/components/layout/activity-pulse.tsx` |
| 0.4 | Add `signature_is_solo` to TS OperationalSettings | MED | 2 min | `dashboard/types/index.ts` |
| 0.5 | Remove misplaced notification fields from TS InboundMailSettings | MED | 5 min | `dashboard/types/index.ts` |
| 0.6 | Add `low_resource_mode` to _ALLOWED_SETTINGS_FIELDS | LOW | 2 min | `app/services/settings/operational_settings_service.py` |
| 0.7 | Add `kapso_api_key` to TS CredentialsStatus | LOW | 2 min | `dashboard/types/index.ts` |
| 0.8 | Fix DbSession type alias to use Session | MED | 2 min | `app/api/v1/settings/operational.py` |
| 0.9 | Use crontab for weekly report schedule | LOW | 5 min | `app/workers/celery_app.py` |
| 0.10 | Replace 12 bare except:pass with logger.debug | MED | 30 min | 11 files |

---

## Phase 1 — Consolidation (2-3 hours)

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 1.1 | Extract shared NotificationListView from security + notifications | MED | 1-2 hrs | NEW: `components/shared/notification-list-view.tsx` |
| 1.2 | Extract _track_failure to shared worker helper | MED | 1 hr | `app/workers/_helpers.py`, 3 worker files |
| 1.3 | Create public send_message_to_phone in whatsapp_service | HIGH | 1 hr | `app/services/comms/whatsapp_service.py`, `app/api/v1/ai_office.py` |

---

## Phase 2 — Scalability (2-3 days)

| # | Task | Effort | Files |
|---|------|--------|-------|
| 2.1 | Add backend geo endpoint for getLeadsWithCoords | 1 day | `app/api/v1/leads.py`, `dashboard/lib/api/client.ts`, `dashboard/app/map/page.tsx` |
| 2.2 | Add server-side leads-with-research for dossiers | 1 day | `app/api/v1/leads.py`, `dashboard/app/dossiers/page.tsx` |
| 2.3 | Add pagination to outreach + responses pages | 2 hrs | `dashboard/app/outreach/page.tsx`, `dashboard/app/responses/page.tsx` |
| 2.4 | Upgrade crypto to PBKDF2HMAC | 1 day | `app/core/crypto.py`, data migration |

---

## Phase 3 — Testing Infrastructure (3-5 days)

| # | Task | Effort | Priority |
|---|------|--------|----------|
| 3.1 | Add frontend component tests (leads, AI office, onboarding) | 2-3 days | P1 |
| 3.2 | Add Celery integration tests (at least full pipeline chain) | 1-2 days | P1 |
| 3.3 | Add tests for Telegram, Territories, Notifications endpoints | 1 day | P2 |
| 3.4 | Extract shared test data seeding to conftest fixtures | 1 hr | P2 |
| 3.5 | Write 3 ADRs for key architecture decisions | 1-2 days | P3 |

---

## Phase 4 — Docs Freshness

| # | Task | Effort |
|---|------|--------|
| 4.1 | Fix stale README metrics (services count, TS files, agent docs) | 15 min |
| 4.2 | Update architecture audit test count (299 → 315) | 5 min |
| 4.3 | Update hardening plan baseline numbers | 5 min |

---

## Expected Score Impact

| Phase | Score After |
|-------|-----------|
| Phase 0 (quick wins) | 8.5 → **9/10** |
| Phase 1 (consolidation) | 9 → **9.3/10** |
| Phase 2 (scalability) | 9.3 → **9.5/10** |
| Phase 3 (testing) | 9.5 → **9.8/10** |
| Phase 4 (docs) | 9.8 → **10/10** |

---

## Commit Strategy

All changes follow conventional commits (AGENTS.md):
- `fix(scope):` for correctness fixes
- `refactor(scope):` for consolidation
- `feat(scope):` for new endpoints
- `test(scope):` for test additions
- `docs(scope):` for documentation

---

## Definition of Done

- ✅ `pytest -q` passes (315+ tests, PostgreSQL)
- ✅ `npx tsc --noEmit` clean
- ✅ No HIGH severity findings remaining
- ✅ All quick wins implemented
- ✅ README metrics accurate
- ✅ Docs internally consistent

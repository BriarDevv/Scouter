# Security Audit — Pending Findings

> Original audit: 2026-03-14 (commit `57f87b7`)
> Agent OS hardening: 2026-04-04 (10 additional fixes, see below)
> Phase 3 hardening: 2026-04-04 (2 additional fixes, see below)
> Remaining: 5 items (1 HIGH, 3 MEDIUM, 1 LOW)

This document lists security findings from the comprehensive audit that were
**not corrected** in the current phase. Each entry explains why it was deferred
and what the recommended next step is.

---

## HIGH severity

### SEC-1 — SMTP/IMAP passwords stored in plaintext in DB

**Table:** `mail_credentials`
**Risk:** If an attacker gains read access to the database (SQL injection, backup
leak, misconfigured replica), all mail passwords are immediately usable.

**Why deferred:** Requires Fernet symmetric encryption with a dedicated
`CREDENTIAL_ENCRYPTION_KEY`, a data migration to encrypt existing rows, and
key-management discipline (env-only, never logged). The change is invasive and
should be tested thoroughly.

**Recommended next step:**
1. Add `cryptography` dependency.
2. Create `app/core/credential_vault.py` with `encrypt()`/`decrypt()` using
   Fernet and a key from `settings.CREDENTIAL_ENCRYPTION_KEY`.
3. Change `MailCredential` model to store `encrypted_password` (bytes) instead
   of `password` (string).
4. Write an Alembic migration that encrypts existing plaintext passwords in-place.
5. Update all read paths (`imap_provider.py`, `smtp_provider.py`) to decrypt
   on use.

---

### SEC-9 — No API authentication

**Risk:** Any network-reachable client can call every API endpoint, including
lead management, outreach sending, and settings changes. Currently mitigated by
running on `localhost` only and being a single-user tool.

**Why deferred:** Adding authentication (API key, JWT, or session-based) is an
architectural change that touches every route and the frontend. Not appropriate
as a patch during a hardening audit.

**Recommended next step:**
1. For v1 single-user: add a simple `X-API-Key` header check via FastAPI
   dependency, with the key stored in `.env`.
2. For multi-user (v2): implement JWT auth with user model, login endpoint,
   and role-based access control.

---

## MEDIUM severity

### PI-6/7/8/10/12 — Crawled data, signals, and opsctl inputs without extra sanitization

**Affected surfaces:**
- Business names and signals injected into LLM prompts (PI-6, PI-7)
- Website/Instagram crawled content (PI-8)
- opsctl snapshot data (PI-10)
- Thread context in reply generation (PI-12)

**Current mitigation:** All external data is already wrapped in `<external_data>`
tags within the **user** message role, with the anti-injection preamble in the
**system** role. This provides structural isolation. The risk is residual —
a sufficiently advanced injection within `<external_data>` could still influence
a less-robust local model.

**Why deferred:** Adding input-level sanitization (stripping control characters,
length limits, pattern detection) requires defining a sanitization policy per
data type without breaking legitimate business names or email content.

**Recommended next step:**
1. Add `app/core/sanitize.py` with `sanitize_external_text(text, max_len)`
   that strips null bytes, CRLF sequences, and excessive whitespace.
2. Apply it at ingestion boundaries (crawlers, IMAP sync, API inputs).
3. Consider a prompt-injection detection heuristic (keyword density for
   "ignore", "system", "override") that flags suspicious inputs for reviewer
   escalation.

---

### CC-7 — No limit on re-sends after failure

**Risk:** If an outreach or reply send keeps failing (e.g., bad SMTP config),
there is no cap on how many FAILED delivery records accumulate per draft, nor
an automatic circuit-breaker.

**Why deferred:** Requires defining a policy (max N retries? exponential
backoff? per-draft vs global?) and deciding on UX (show "permanently failed"
state in dashboard?). Not a quick patch.

**Recommended next step:**
1. Add `max_send_attempts` to `OperationalSettings` (default: 3).
2. In `send_draft()` and `send_reply_assistant_draft()`, count existing FAILED
   deliveries/sends for the same draft and refuse if >= max.
3. Surface a `permanently_failed` status in the frontend.

---

### CC-8 — Subject-based fallback matching can link to wrong lead

**Risk:** When inbound mail matching falls back to subject line + sender email
(no `In-Reply-To` or `References` header), a lead who happens to reply to an
unrelated email with a similar subject could get incorrectly linked.

**Current mitigation:** The fallback is a last resort after Message-ID and
References matching fail. In practice, subject + email is reasonably unique.

**Why deferred:** Adding a time window (e.g., only match if the outreach was
sent within the last 30 days) requires a schema-aware query change and testing
with real mail flows.

**Recommended next step:**
1. Add a `WHERE sent_at > now() - interval '30 days'` condition to the
   subject-based fallback query in `inbound_mail_service.py`.
2. Consider also requiring a minimum subject similarity threshold (Levenshtein
   or token overlap) instead of exact match.

---

## LOW severity

### A-4 — URL href without protocol validation in frontend

**Risk:** If a lead's `website_url` contains a `javascript:` or `data:` URI,
clicking it in the dashboard could execute arbitrary code in the operator's
browser.

**Current mitigation:** URLs come from controlled crawlers and manual input,
not from untrusted external users. The risk is low but non-zero.

**Why deferred:** Requires a frontend-side utility and applying it to every
`<a href>` that renders external URLs. Low effort but low priority.

**Recommended next step:**
1. Add a `sanitizeUrl(url)` utility in `dashboard/lib/utils.ts` that returns
   `#` for any URL not starting with `http://`, `https://`, or `mailto:`.
2. Apply it to all external-URL link components.

---

## Resolved post-audit (Phase 3 hardening, 2026-04-04)

| Finding | Fix | Commit |
|---------|-----|--------|
| API key visible in structured log output | `api_key` added to scrubbing regex in `app/core/logging.py` | Phase 3 |
| `decrypt_safe()` silent on invalid token | Now logs a warning before returning original value, making decryption failures observable | Phase 3 |

## Resolved post-audit (Agent OS hardening, 2026-04-04)

| Finding | Fix | Commit |
|---------|-----|--------|
| SSRF in Scout tools (browse_page, extract_contacts, etc.) | `_validate_url()` blocks private IPs, loopback, reserved ranges, dangerous schemes | Agent OS implementation |
| Prompt injection in Closer service | `_sanitize_client_message()` + `<client_message>` delimiters in system prompt | Agent OS implementation |
| WhatsApp test endpoint: phone in query params | Moved to POST body with Pydantic validation (`TestWhatsAppBody`) | `5a894d7` |
| WhatsApp test endpoint: no input validation | Phone format validation (8-16 digits), message length cap (500 chars) | Agent OS implementation |
| Pipeline context size unbounded | `context_service.py`: 2KB per step, 16KB total limits | Agent OS implementation |
| Next.js proxy: open SSRF | Path allowlist (23 prefixes) + `..`/`//` traversal guard | `ed1c873`, `d6f46ed` |
| Setup actions: no rate limiting | 5-second cooldown between POST actions | `ed1c873` |
| Silent `except: pass` hiding errors | Replaced with `logger.debug()` in research_tasks, agent/core, closer_service | `bcde504` |
| Closer prompt hardcoded outside registry | Moved to `app/llm/prompts.py` as `CLOSER_RESPONSE_SYSTEM` | `2b80ac9` |
| Output sanitization weak | URL credential stripping regex + 2KB output cap in `_sanitize_output` | `ed1c873` |

---

## Already resolved in this audit

For reference, the following findings were **fixed** in commit `57f87b7` and
the associated migration:

| ID | Severity | Summary | Fix |
|----|----------|---------|-----|
| PI-1/2/3/4/5 | CRITICAL | Flat prompt injection via `/api/generate` | Migrated to `/api/chat` with system/user role separation + `<external_data>` tags + anti-injection preamble |
| CC-1 | CRITICAL | Double-send of outreach drafts | Partial unique index on `outreach_deliveries` (this migration) + IntegrityError handling |
| CC-2 | HIGH | Inbound sync crash on duplicate | IntegrityError catch with rollback in `_persist_inbound_message()` |
| CC-3 | HIGH | Reply draft regeneration while send active | Guard in `generate_reply_assistant_draft()` |
| CC-6 | HIGH | Stuck SENDING records block pipeline | 5-minute timeout recovery |
| SEC-2 | HIGH | Default SECRET_KEY in production | Validator warning on startup |
| SEC-3 | HIGH | Hardcoded DB password in alembic.ini | Replaced with placeholder |
| SEC-5 | HIGH | Raw SMTP errors leak credentials | Sanitized error messages |
| SEC-10 | HIGH | Sensitive values in structlog output | Key-based scrubbing processor |
| B-2 | HIGH | CRLF injection in email subjects | Stripping in smtp_provider + reply_send_service |
| CC-9 | MEDIUM | Re-classification of already-classified messages | Status gate in `classify_inbound_message()` |

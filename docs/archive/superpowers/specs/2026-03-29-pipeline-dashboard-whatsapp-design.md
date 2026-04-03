# Pipeline Inteligente + Dashboard WhatsApp — Design Spec

## Problem

The pipeline only generates email drafts. Leads with phone numbers (from Google Maps) get no WhatsApp outreach. The dashboard doesn't distinguish between email and WhatsApp drafts, and there's no configuration UI for Kapso/WhatsApp outreach.

## Decision Log

- **Dual channel**: if lead has email → email draft, if has phone → WhatsApp draft, both if both
- **Config level**: Simple — toggle on/off + test connection (API key stays in .env for security)
- **Security**: API key never stored in DB, never exposed via API, parameterized queries only

## Components

### 1. Pipeline: Smart draft generation

Modify `app/workers/tasks.py: task_generate_draft` to also generate WhatsApp drafts:

```python
# After existing email draft generation:
if lead.phone and wa_outreach_enabled:
    generate_whatsapp_draft(db, lead.id)
```

Check `whatsapp_outreach_enabled` from OperationalSettings before generating WA drafts.

New setting field: `whatsapp_outreach_enabled: bool = False` in OperationalSettings model + migration.

### 2. Settings: Kapso configuration section

New section in Settings page (`/settings`):

- **Status indicator**: green/red dot showing if KAPSO_API_KEY is configured
- **Test connection button**: POST to `/api/v1/settings/test/kapso` → tries Kapso API health check
- **Toggle**: `whatsapp_outreach_enabled` — enables/disables WA draft generation in pipeline
- **Info text**: "La API key se configura en .env por seguridad"

Backend:
- New endpoint: `POST /api/v1/settings/test/kapso` — tests Kapso API connectivity
- OperationalSettings field: `whatsapp_outreach_enabled`
- API key presence check: `GET /api/v1/settings/credentials` already returns presence flags — add `kapso_api_key` to it

### 3. Outreach page: Channel badges + filter

Modify outreach page:

- Badge per draft: "Email" (blue) or "WA" (green) based on `draft.channel`
- Tab filter: Todos / Email / WhatsApp (in addition to existing status tabs)
- Draft detail: hide subject field when `channel="whatsapp"`
- Send button: "Enviar por WhatsApp" for WA drafts

### Security

- **API key**: stored in `.env` only, never in DB, never returned by any API endpoint
- **Prompt injection**: WhatsApp draft prompts use `<external_data>` tags + `ANTI_INJECTION_PREAMBLE` (same as email)
- **DB**: all queries use SQLAlchemy ORM with parameterized queries — no raw SQL string interpolation
- **Phone masking**: phone numbers logged with last 4 digits masked (e.g., `+5411***1234`)
- **Rate limiting**: existing API rate limiter applies to all new endpoints

## Out of scope

- Storing Kapso API key in DB (stays in .env)
- WhatsApp Business templates
- Reply tracking from WhatsApp
- Multimedia messages

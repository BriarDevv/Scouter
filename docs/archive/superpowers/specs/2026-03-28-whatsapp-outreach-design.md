# WhatsApp Outreach to Leads — Design Spec

## Problem

Scouter can generate email outreach drafts but has no way to reach leads via WhatsApp. Many Argentine SMBs (the target market) are more responsive to WhatsApp than email. The system needs a WhatsApp outreach channel with LLM-generated draft messages, human-in-the-loop approval, and delivery via Kapso API.

## Decision Log

- **Draft type**: WhatsApp-specific (short, conversational), not email reuse
- **Phone source**: `Lead.phone` from Google Maps crawl (field already exists)
- **Provider**: Kapso ($25/100K msgs, REST API, professional)
- **Approval flow**: Human-in-the-loop always (same as email)
- **LLM roles**: Maintained — EXECUTOR (9B) generates, REVIEWER (27B) reviews, AGENT (Hermes 3 8B) orchestrates

## Architecture

```
Lead.phone (from Google Maps crawl)
    ↓
EXECUTOR (9B) generates WhatsApp draft (max 300 chars, conversational)
    ↓
OutreachDraft (channel="whatsapp", status=pending_review)
    ↓
Human approves via dashboard or Hermes chat
    ↓
kapso_service.send_whatsapp_message(phone, body)
    ↓
OutreachDelivery (provider="kapso", status tracking)
```

## Components

### 1. OutreachDraft — add `channel` field

Add `channel` column to `OutreachDraft` model:

```python
channel: Mapped[str] = mapped_column(String(20), default="email", nullable=False)
```

- Default: `"email"` (backward compatible)
- WhatsApp drafts: `channel="whatsapp"`, `subject=None`
- All existing approve/reject/review logic works unchanged

Alembic migration to add the column with `server_default="email"`.

### 2. WhatsApp draft prompt

New prompt pair in `app/llm/prompts.py`:

- `GENERATE_WHATSAPP_DRAFT_SYSTEM`: instructs EXECUTOR to write a short (max 300 char) conversational WhatsApp message in rioplatense Spanish
- `GENERATE_WHATSAPP_DRAFT_DATA`: provides lead context (business_name, industry, city, signals, llm_summary, llm_suggested_angle)
- Output format: `{"body": "..."}`
- No subject field
- Tone: casual-professional, "vos", direct, no email formalities
- Must NOT include URLs unless provided in brand context

### 3. WhatsApp draft generator

New function in `app/outreach/generator.py`:

```python
def generate_whatsapp_draft_content(lead: Lead, db: Session | None = None) -> str:
    """Generate WhatsApp message body via EXECUTOR model."""
```

- Similar to `generate_draft_content()` but uses WhatsApp prompt
- Returns only `body` (no subject)
- Word count validation: max 80 words (WhatsApp is short)
- URL fabrication check (same as email)

### 4. Kapso service

New file: `app/services/kapso_service.py`

```python
def send_whatsapp_message(phone: str, message: str) -> dict:
    """Send a WhatsApp message via Kapso API."""
```

- POST to `https://api.kapso.ai/meta/whatsapp/messages`
- Auth: `X-API-Key: {KAPSO_API_KEY}` header
- Body: `{"to": phone, "type": "text", "text": {"body": message}}`
- Returns: `{"message_id": "...", "status": "sent"}`
- Error handling: raises `KapsoError` on failure

Config additions to `app/core/config.py`:
- `KAPSO_API_KEY: str | None = None`
- `KAPSO_BASE_URL: str = "https://api.kapso.ai/meta/whatsapp"`

### 5. Outreach service changes

Update `app/services/outreach_service.py`:

```python
def generate_whatsapp_draft(db: Session, lead_id: UUID) -> OutreachDraft | None:
    """Generate a WhatsApp outreach draft for a lead."""
```

- Validates lead has phone number
- Calls `generate_whatsapp_draft_content(lead)`
- Creates `OutreachDraft(channel="whatsapp", subject=None, body=body)`
- Logs as `GENERATED` in OutreachLog

```python
def send_whatsapp_draft(db: Session, draft_id: UUID) -> OutreachDelivery:
    """Send an approved WhatsApp draft via Kapso."""
```

- Validates draft is approved + channel is whatsapp
- Calls `kapso_service.send_whatsapp_message(lead.phone, draft.body)`
- Creates `OutreachDelivery(provider="kapso", recipient_email=lead.phone)`
- Updates draft status to SENT

### 6. Agent tools

New tools in `app/agent/tools/outreach.py`:

- `generate_whatsapp_draft(lead_id)` — generates WhatsApp draft, requires confirmation
- `send_whatsapp_draft(draft_id)` — sends via Kapso, requires confirmation

Existing tools unchanged — `approve_draft` and `reject_draft` work for both email and WhatsApp.

### 7. Dashboard changes

Minimal UI changes:
- Outreach page: add "WA" badge next to WhatsApp drafts
- Draft detail: hide subject field when `channel="whatsapp"`
- No new pages needed

## Out of scope (v1)

- WhatsApp Business templates (requires Meta approval)
- Reply tracking from WhatsApp
- Multimedia messages (images, PDFs)
- Read/delivered receipts
- Auto-follow-up sequences

## Config requirements

```env
# .env additions
KAPSO_API_KEY=your-kapso-api-key
KAPSO_BASE_URL=https://api.kapso.ai/meta/whatsapp  # default
```

## Verification

1. `pytest` — all tests pass including new WhatsApp draft tests
2. Generate WhatsApp draft for lead with phone → draft created with channel="whatsapp"
3. Approve draft → status changes to approved
4. Send draft → Kapso API called, delivery recorded
5. Dashboard shows draft with "WA" badge
6. Hermes: "genera un draft de whatsapp para [lead]" → tool called correctly
7. `npx tsc --noEmit` — zero type errors

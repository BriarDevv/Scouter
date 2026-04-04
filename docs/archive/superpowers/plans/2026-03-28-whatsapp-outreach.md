# WhatsApp Outreach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable sending LLM-generated WhatsApp outreach messages to leads via Kapso API, with human-in-the-loop approval.

**Architecture:** Add `channel` field to `OutreachDraft`, new WhatsApp-specific LLM prompt (short, conversational), new `kapso_service.py` for delivery, new agent tools. All existing approve/reject flows work unchanged.

**Tech Stack:** Python 3.12, SQLAlchemy, Ollama (EXECUTOR 9B), Kapso REST API, httpx

---

### Task 1: Add `channel` column to OutreachDraft model

**Files:**
- Modify: `app/models/outreach.py:25`
- Create: `alembic/versions/a1b2c3d4e5f7_add_draft_channel.py`

- [ ] **Step 1: Add column to model**

In `app/models/outreach.py`, after the `body` column (line 26), add:

```python
channel: Mapped[str] = mapped_column(String(20), default="email", nullable=False)
```

Change `subject` from `nullable=False` to `nullable=True` (WhatsApp drafts have no subject):

```python
subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

- [ ] **Step 2: Create migration**

Create `alembic/versions/a1b2c3d4e5f7_add_draft_channel.py`:

```python
"""add channel column to outreach_drafts

Revision ID: a1b2c3d4e5f7
Revises: f7a8b9c0d1e2
Create Date: 2026-03-28 23:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "outreach_drafts",
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
    )
    op.alter_column("outreach_drafts", "subject", nullable=True)

def downgrade() -> None:
    op.alter_column("outreach_drafts", "subject", nullable=False)
    op.drop_column("outreach_drafts", "channel")
```

- [ ] **Step 3: Verify import**

Run: `python -c "from app.models.outreach import OutreachDraft; print(OutreachDraft.channel.property.columns[0].default.arg)"`

Expected: `email`

- [ ] **Step 4: Commit**

```bash
git add app/models/outreach.py alembic/versions/a1b2c3d4e5f7_add_draft_channel.py
git commit -m "feat: add channel column to OutreachDraft (email/whatsapp)"
```

---

### Task 2: WhatsApp draft LLM prompt

**Files:**
- Modify: `app/llm/prompts.py` (append)
- Modify: `app/llm/client.py` (append)

- [ ] **Step 1: Add WhatsApp prompt templates**

Append to `app/llm/prompts.py`:

```python
GENERATE_WHATSAPP_DRAFT_SYSTEM = ANTI_INJECTION_PREAMBLE + """
Sos un experto en ventas de servicios de desarrollo web. Generá un mensaje de WhatsApp
corto y conversacional en español rioplatense (Argentina) para contactar a un posible cliente.

Reglas:
- MÁXIMO 300 caracteres (es un mensaje de WhatsApp, no un email)
- Tono casual-profesional: usá "vos", sé directo, sin formalidades de email
- NO incluyas asunto (WhatsApp no tiene asunto)
- NO inventes URLs — solo usá las que se proporcionan en el contexto
- NO uses "Estimado/a", "A quien corresponda", ni saludos formales
- Empezá con un saludo natural: "Hola!", "Buenas!", "Qué tal!"
- Mencioná el nombre del negocio y por qué lo contactás
- Cerrá con una pregunta o invitación a charlar

Respondé SOLO con JSON:
{
  "body": "El mensaje de WhatsApp completo"
}
"""

GENERATE_WHATSAPP_DRAFT_DATA = """
<external_data>
Negocio: {business_name}
Rubro: {industry}
Ciudad: {city}
Sitio web: {website_url}
Instagram: {instagram_url}
Resumen IA: {llm_summary}
Ángulo sugerido: {llm_suggested_angle}
Señales detectadas: {signals}
</external_data>
"""
```

- [ ] **Step 2: Add client function**

Append to `app/llm/client.py`:

```python
def generate_whatsapp_draft(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> dict:
    """Generate a WhatsApp outreach message. Returns dict with body."""
    user_prompt = GENERATE_WHATSAPP_DRAFT_DATA.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        llm_summary=llm_summary or "No summary available",
        llm_suggested_angle=llm_suggested_angle or "Web development services",
        signals=_format_signals(signals),
    )

    fallback = {
        "body": f"Hola! Vi que {business_name} podría mejorar su presencia digital. "
        "Te interesaría charlar sobre cómo puedo ayudarte? 🚀",
    }

    try:
        raw = _call_ollama_chat(
            GENERATE_WHATSAPP_DRAFT_SYSTEM, user_prompt, role=role,
        )
        data = _extract_json(raw)
        body = data.get("body")
        if not body:
            raise LLMParseError("Missing body in WhatsApp draft response")
        return {"body": body}
    except Exception as e:
        logger.error("llm_whatsapp_draft_failed", role=_role_value(role), error=str(e))
        return fallback
```

Add the import at the top of client.py:

```python
from app.llm.prompts import (
    # ... existing imports ...
    GENERATE_WHATSAPP_DRAFT_DATA,
    GENERATE_WHATSAPP_DRAFT_SYSTEM,
)
```

- [ ] **Step 3: Verify import**

Run: `python -c "from app.llm.client import generate_whatsapp_draft; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/llm/prompts.py app/llm/client.py
git commit -m "feat: add WhatsApp draft generation prompt + LLM client function"
```

---

### Task 3: WhatsApp draft generator with validation

**Files:**
- Modify: `app/outreach/generator.py` (append)

- [ ] **Step 1: Add WhatsApp generator function**

Append to `app/outreach/generator.py`:

```python
WA_WORD_LIMIT = 80
WA_CHAR_LIMIT = 300


def generate_whatsapp_draft_content(lead: Lead, db: Session | None = None) -> str:
    """Generate WhatsApp message body via EXECUTOR model. Returns body string."""
    from app.llm.client import generate_whatsapp_draft as llm_wa_generate

    brand_ctx = get_brand_context(db) if db is not None else None
    result = llm_wa_generate(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        llm_summary=lead.llm_summary,
        llm_suggested_angle=lead.llm_suggested_angle,
        signals=list(lead.signals),
    )

    body = result["body"]
    warnings: list[str] = []

    # Word count check
    if len(body.split()) > WA_WORD_LIMIT:
        warnings.append(f"wa_body_words={len(body.split())} (limit {WA_WORD_LIMIT})")

    # Char limit check — truncate if needed
    if len(body) > WA_CHAR_LIMIT:
        body = body[:WA_CHAR_LIMIT - 3] + "..."
        warnings.append(f"wa_body_truncated_at={WA_CHAR_LIMIT}")

    # URL fabrication check
    allowed = _collect_allowed_urls(lead, brand_ctx)
    for url in _URL_RE.findall(body):
        clean = url.rstrip("/.,;:!?")
        if not any(clean.startswith(a) for a in allowed):
            body = body.replace(url, "")
            warnings.append(f"fabricated_url_removed={url}")

    if warnings:
        logger.warning("wa_draft_validation_warnings", lead_id=str(lead.id), warnings=warnings)

    return body.strip()
```

- [ ] **Step 2: Verify import**

Run: `python -c "from app.outreach.generator import generate_whatsapp_draft_content; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/outreach/generator.py
git commit -m "feat: add WhatsApp draft generator with validation"
```

---

### Task 4: Kapso service

**Files:**
- Create: `app/services/kapso_service.py`
- Modify: `app/core/config.py`

- [ ] **Step 1: Add config vars**

In `app/core/config.py`, add after the WhatsApp section:

```python
# Kapso (WhatsApp outreach)
KAPSO_API_KEY: str | None = None
KAPSO_BASE_URL: str = "https://api.kapso.ai/meta/whatsapp"
```

- [ ] **Step 2: Create Kapso service**

Create `app/services/kapso_service.py`:

```python
"""Kapso WhatsApp API client for outreach delivery."""

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KapsoError(Exception):
    """Error communicating with Kapso API."""
    pass


def send_whatsapp_message(phone: str, message: str) -> dict:
    """Send a text message via Kapso WhatsApp API.

    Args:
        phone: Recipient phone number (E.164 format preferred)
        message: Text message body

    Returns:
        Dict with message_id and status from Kapso response.

    Raises:
        KapsoError: If API key is missing or request fails.
    """
    if not settings.KAPSO_API_KEY:
        raise KapsoError("KAPSO_API_KEY not configured")

    url = f"{settings.KAPSO_BASE_URL}/messages"
    headers = {
        "X-API-Key": settings.KAPSO_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    logger.info("kapso_send_request", phone=phone[:6] + "***", body_len=len(message))

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("kapso_send_success", phone=phone[:6] + "***", message_id=data.get("id"))
            return {
                "message_id": data.get("id"),
                "status": "sent",
            }
    except httpx.HTTPStatusError as exc:
        logger.error("kapso_send_http_error", status=exc.response.status_code)
        raise KapsoError(f"Kapso API error: {exc.response.status_code}") from exc
    except httpx.ConnectError as exc:
        logger.error("kapso_send_connect_error")
        raise KapsoError("No se pudo conectar a Kapso") from exc
```

- [ ] **Step 3: Verify import**

Run: `python -c "from app.services.kapso_service import send_whatsapp_message, KapsoError; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/core/config.py app/services/kapso_service.py
git commit -m "feat: add Kapso WhatsApp API service"
```

---

### Task 5: Outreach service — WhatsApp draft + send

**Files:**
- Modify: `app/services/outreach_service.py` (append)

- [ ] **Step 1: Add generate_whatsapp_draft function**

Append to `app/services/outreach_service.py`:

```python
def generate_whatsapp_draft(db: Session, lead_id: uuid.UUID) -> OutreachDraft | None:
    """Generate a WhatsApp outreach draft for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    if not lead.phone:
        logger.warning(
            "wa_draft_skipped_no_phone", lead_id=str(lead_id), business=lead.business_name,
        )
        return None

    from app.outreach.generator import generate_whatsapp_draft_content

    body = generate_whatsapp_draft_content(lead, db=db)

    draft = OutreachDraft(
        lead_id=lead.id,
        channel="whatsapp",
        subject=None,
        body=body,
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)
    db.flush()

    db.add(OutreachLog(
        lead_id=lead.id,
        draft_id=draft.id,
        action=LogAction.GENERATED,
        actor="system",
    ))

    db.commit()
    db.refresh(draft)
    logger.info("wa_draft_generated", lead_id=str(lead_id), draft_id=str(draft.id))
    return draft


def send_whatsapp_draft(db: Session, draft_id: uuid.UUID) -> OutreachDelivery:
    """Send an approved WhatsApp draft via Kapso."""
    from app.models.outreach_delivery import OutreachDelivery
    from app.services.kapso_service import KapsoError, send_whatsapp_message

    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        raise ValueError("Draft not found")
    if draft.channel != "whatsapp":
        raise ValueError("Draft is not a WhatsApp draft")
    if draft.status != DraftStatus.APPROVED:
        raise ValueError(f"Draft status is {draft.status.value}, expected approved")

    lead = db.get(Lead, draft.lead_id)
    if not lead or not lead.phone:
        raise ValueError("Lead has no phone number")

    # Send via Kapso
    result = send_whatsapp_message(lead.phone, draft.body)

    # Record delivery
    delivery = OutreachDelivery(
        draft_id=draft.id,
        lead_id=lead.id,
        recipient_email=lead.phone,  # reuse field for phone
        provider="kapso",
        external_message_id=result.get("message_id"),
    )
    db.add(delivery)

    # Update draft status
    draft.status = DraftStatus.SENT
    draft.sent_at = datetime.now(timezone.utc)

    # Log
    db.add(OutreachLog(
        lead_id=lead.id,
        draft_id=draft.id,
        action=LogAction.SENT,
        actor="system",
    ))

    # Update lead status to CONTACTED
    if lead.status not in (
        LeadStatus.CONTACTED, LeadStatus.OPENED, LeadStatus.REPLIED,
        LeadStatus.MEETING, LeadStatus.WON, LeadStatus.LOST,
    ):
        lead.status = LeadStatus.CONTACTED

    db.commit()
    db.refresh(delivery)
    logger.info("wa_draft_sent", draft_id=str(draft_id), phone=lead.phone[:6] + "***")
    return delivery
```

Add missing import at top of file:

```python
from datetime import datetime, timezone
```

- [ ] **Step 2: Verify import**

Run: `python -c "from app.services.outreach_service import generate_whatsapp_draft, send_whatsapp_draft; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/services/outreach_service.py
git commit -m "feat: add WhatsApp draft generation + Kapso delivery in outreach service"
```

---

### Task 6: Agent tools for WhatsApp

**Files:**
- Modify: `app/agent/tools/outreach.py` (append)

- [ ] **Step 1: Add WhatsApp tools**

Append to `app/agent/tools/outreach.py`:

```python
# ---------------------------------------------------------------------------
# WhatsApp draft tools
# ---------------------------------------------------------------------------


def generate_whatsapp_draft(db: Session, *, lead_id: str) -> dict:
    """Generate a WhatsApp outreach draft for a lead."""
    from app.services.outreach_service import generate_whatsapp_draft as _gen_wa

    try:
        lid = uuid.UUID(lead_id)
    except ValueError:
        return {"error": "ID de lead inválido"}
    draft = _gen_wa(db, lid)
    if not draft:
        return {"error": "No se pudo generar (lead no encontrado o sin teléfono)"}
    return {
        "id": str(draft.id),
        "channel": "whatsapp",
        "body": draft.body,
        "status": draft.status.value,
    }


def send_whatsapp_draft(db: Session, *, draft_id: str) -> dict:
    """Send an approved WhatsApp draft via Kapso."""
    from app.services.outreach_service import send_whatsapp_draft as _send_wa

    try:
        did = uuid.UUID(draft_id)
    except ValueError:
        return {"error": "ID de borrador inválido"}
    try:
        delivery = _send_wa(db, did)
        return {
            "id": str(delivery.id),
            "status": "sent",
            "recipient_phone": delivery.recipient_email,
            "provider": "kapso",
        }
    except Exception as exc:
        return {"error": str(exc)}


registry.register(ToolDefinition(
    name="generate_whatsapp_draft",
    description=(
        "Generar un borrador de mensaje WhatsApp para un lead "
        "(requiere confirmación — el lead debe tener teléfono)"
    ),
    parameters=[
        ToolParameter("lead_id", "string", "UUID del lead"),
    ],
    category="outreach",
    requires_confirmation=True,
    handler=generate_whatsapp_draft,
))

registry.register(ToolDefinition(
    name="send_whatsapp_draft",
    description=(
        "Enviar un borrador de WhatsApp aprobado via Kapso "
        "(requiere confirmación — envía mensaje real)"
    ),
    parameters=[
        ToolParameter("draft_id", "string", "UUID del borrador de WhatsApp"),
    ],
    category="outreach",
    requires_confirmation=True,
    handler=send_whatsapp_draft,
))
```

- [ ] **Step 2: Verify tools register**

Run: `python -c "from app.agent.tools import *; from app.agent.tool_registry import registry; print(f'{len(registry.list_all())} tools'); print('generate_whatsapp_draft' in [t.name for t in registry.list_all()]); print('send_whatsapp_draft' in [t.name for t in registry.list_all()])"`

Expected: `50 tools`, `True`, `True`

- [ ] **Step 3: Commit**

```bash
git add app/agent/tools/outreach.py
git commit -m "feat: add generate_whatsapp_draft + send_whatsapp_draft agent tools"
```

---

### Task 7: Update .env.example + run migration

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add Kapso config to .env.example**

Append to `.env.example`:

```env
# ── Kapso (WhatsApp outreach to leads)
KAPSO_API_KEY=
KAPSO_BASE_URL=https://api.kapso.ai/meta/whatsapp
```

- [ ] **Step 2: Run migration in WSL**

```bash
wsl.exe -- bash -lc "cd ~/src/Scouter && source .venv/bin/activate && alembic upgrade head"
```

Expected: `Running upgrade ... -> a1b2c3d4e5f7, add channel column to outreach_drafts`

- [ ] **Step 3: Verify column exists**

```bash
wsl.exe -- bash -lc "cd ~/src/Scouter && source .venv/bin/activate && python3 -c \"
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
r = db.execute(text(\\\"SELECT column_name FROM information_schema.columns WHERE table_name='outreach_drafts' AND column_name='channel'\\\")).scalar()
print(f'channel column: {r}')
db.close()
\""
```

Expected: `channel column: channel`

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "chore: add Kapso config to .env.example"
```

---

### Task 8: Full test run + push

- [ ] **Step 1: Run backend tests**

```bash
wsl.exe -- bash -lc "cd ~/src/Scouter && source .venv/bin/activate && python3 -m pytest tests/ --tb=short"
```

Expected: 133+ passed, 0 failed

- [ ] **Step 2: Run TypeScript check**

```bash
cd dashboard && node node_modules/typescript/bin/tsc --noEmit
```

Expected: exit 0

- [ ] **Step 3: Test agent tool registration**

```bash
python -c "from app.agent.tools import *; from app.agent.tool_registry import registry; print(f'{len(registry.list_all())} tools')"
```

Expected: `50 tools`

- [ ] **Step 4: Push all**

```bash
git push origin main
```

- [ ] **Step 5: Pull + restart in WSL**

```bash
wsl.exe -- bash -lc "cd ~/src/Scouter && git pull origin main && make down && sleep 2 && make up"
```

- [ ] **Step 6: End-to-end test via agent**

```bash
# Create conversation and ask Hermes to generate a WhatsApp draft
wsl.exe -- bash -lc 'CONV=$(curl -s -X POST http://localhost:8000/api/v1/chat/conversations | python3 -c "import sys,json;print(json.load(sys.stdin)[\"id\"])") && curl -s -N --max-time 90 -X POST "http://localhost:8000/api/v1/chat/conversations/$CONV/messages" -H "Content-Type: application/json" -d "{\"content\": \"genera un draft de whatsapp para el lead con mejor score\"}" | grep "tool_start\|tool_result\|confirmation_required\|turn_complete" | head -5'
```

Expected: `confirmation_required` event for `generate_whatsapp_draft`

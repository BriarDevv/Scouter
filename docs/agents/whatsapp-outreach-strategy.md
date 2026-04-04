# WhatsApp Outreach Strategy

**Status:** Designed, pending template approval
**Last updated:** 2026-04-04

---

## Overview

Scouter uses two WhatsApp providers for different purposes:

| Provider | Purpose | Auth | First Message |
|---|---|---|---|
| **CallMeBot** | Operator notifications (alerts, reports) | API key (free) | Any text |
| **Kapso** | Client outreach (sales conversations) | API key (WhatsApp Business API) | Requires Meta-approved template |

---

## The Template Problem

WhatsApp Business API (used by Kapso) requires that the **first message to a new contact** be a pre-approved template. After the client responds, a 24-hour "conversation window" opens for free-form messages.

This means Mote **cannot** send the personalized draft as the first message. The strategy:

```
1. Mote sends TEMPLATE (opens conversation)     ← Meta-approved, generic
2. Client responds                                ← Window opens (24hrs)
3. Mote sends PERSONALIZED DRAFT                 ← From pipeline context
4. Closer mode: free conversation                ← Until window closes
```

---

## Template Strategy

### Recommended Templates (create in Kapso panel)

The AI (Executor 9b) selects the best template based on lead signals:

| Template Name | When to Use | Text |
|---|---|---|
| `apertura_general` | Default / fallback | "Hola {{1}}, soy {{2}} de Scouter. Vi tu negocio y me encantaría mostrarte cómo mejorar tu presencia web. ¿Te copa que te cuente más?" |
| `apertura_instagram` | Signal: INSTAGRAM_ONLY | "Hola {{1}}, vi tu perfil en Instagram y me pareció muy bueno. ¿Sabías que con una web propia podrías convertir seguidores en clientes? Soy {{2}} de Scouter." |
| `apertura_sin_web` | Signal: NO_WEBSITE | "Hola {{1}}, noté que {{2}} todavía no tiene página web. Hoy en día es clave para que te encuentren clientes nuevos. ¿Te interesa saber más?" |
| `apertura_web_vieja` | Signal: OUTDATED_WEBSITE, NO_SSL, NO_MOBILE_FRIENDLY | "Hola {{1}}, estuve viendo el sitio de {{2}} y noté algunas oportunidades de mejora. ¿Te gustaría que te cuente qué se podría hacer?" |
| `seguimiento` | Follow-up after no response (7 days) | "Hola {{1}}, te escribí hace unos días sobre la web de {{2}}. ¿Tuviste chance de pensarlo? Cualquier cosa estoy por acá." |

**Variables:**
- `{{1}}` = contact name or business name
- `{{2}}` = business name or sender name (depends on template)

### Template Selection Logic

```python
# Based on lead signals and context
if "INSTAGRAM_ONLY" in signals:
    template = "apertura_instagram"
elif "NO_WEBSITE" in signals:
    template = "apertura_sin_web"
elif any(s in signals for s in ["OUTDATED_WEBSITE", "NO_SSL", "NO_MOBILE_FRIENDLY"]):
    template = "apertura_web_vieja"
else:
    template = "apertura_general"
```

---

## Conversation Flow

### Phase 1: Template Open (Mote Outreach mode)

```
Pipeline completes → draft generated → template selected
    ↓
Mote sends template via Kapso → opens WhatsApp conversation
    ↓
Lead receives template message
    ↓
If lead responds → 24hr window opens → Phase 2
If no response after 7 days → send "seguimiento" template
```

### Phase 2: Personalized Engagement (Mote Closer mode)

```
Client responds (any message)
    ↓
Intent detection: pricing? meeting? interest? objection?
    ↓
Mote sends personalized draft (from pipeline: research + brief + context)
    ↓
Free conversation for 24 hours
    ↓
Mote uses: dossier, brief, pricing matrix, research findings
Mote can: answer prices, share portfolio, propose meetings, handle objections
    ↓
Operator can take over at any point via /ai-office/conversations/{id}/takeover
```

### Phase 3: Meeting or Close

```
Client shows buying intent → Mote proposes meeting
    ↓
Meeting scheduled → lead status → MEETING
    ↓
Operator takes over for the actual meeting
```

---

## Kapso Configuration

### Creating Templates

1. Log into Kapso dashboard
2. Go to Templates → Create Template
3. Enter template name (e.g., `apertura_general`)
4. Category: `MARKETING` or `UTILITY`
5. Language: `es_AR` (Spanish Argentina)
6. Body: template text with `{{1}}`, `{{2}}` variables
7. Submit for Meta review

### Template Approval

- Simple templates: minutes to a few hours
- Marketing templates: up to 24-48 hours
- Rejected templates: usually too promotional or missing opt-out

### Tips for Approval

- Keep it conversational, not salesy
- Don't promise discounts or limited-time offers
- Include a question (Meta likes interactive templates)
- Don't use ALL CAPS or excessive punctuation

---

## Implementation Status

| Component | Status | Location |
|---|---|---|
| Kapso client (text messages) | Done | `app/services/comms/kapso_service.py` |
| CallMeBot (notifications) | Done + tested | `app/services/comms/whatsapp_service.py` |
| Auto-send service | Done | `app/services/outreach/auto_send_service.py` |
| OutboundConversation model | Done | `app/models/outbound_conversation.py` |
| Closer service (intent + responses) | Done | `app/services/outreach/closer_service.py` |
| Template selection logic | **Pending** | Needs Kapso template API integration |
| Template-first send flow | **Pending** | Needs template IDs from Kapso panel |

### What's Needed to Go Live

1. Create 3-5 templates in Kapso panel
2. Wait for Meta approval
3. Add template IDs to config or DB
4. Implement `send_template_message()` in kapso_service.py
5. Modify auto_send_service to send template first, draft on reply
6. Test end-to-end with operator's number

---

## Runtime Modes

| Mode | Who sends | What happens |
|---|---|---|
| `safe` | Human only | Mote suggests, human sends manually |
| `assisted` | Human approves, system sends | Draft approved → template sent automatically |
| `outreach` | Mote sends first message | Template sent → waits for reply → human takes over |
| `closer` | Mote manages conversation | Template → reply → personalized draft → full conversation |

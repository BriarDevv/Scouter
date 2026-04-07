---
name: scouter-whatsapp
description: "WhatsApp integration status, credential management, and conversational channel configuration for Scouter."
metadata: { "hermes": { "emoji": "💬", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# Scouter WhatsApp Skill

Manage WhatsApp as a notification and conversational channel for Scouter.

## When to use

- "está configurado WhatsApp?"
- "testear conexión de WhatsApp"
- "qué alertas se mandan por WhatsApp?"
- Questions about WhatsApp capabilities, configuration, or status

## When NOT to use

- Sending a WhatsApp message manually → not supported
- Notification queries → use **scouter-notifications**
- Lead/draft data → use **scouter-data**

## Capabilities

WhatsApp integration has 3 stages:
1. **Alerts** (Etapa 1) — outbound alerts to operator's phone based on severity/category thresholds
2. **Conversational** (Etapa 2) — read-only queries via WhatsApp (leads, notifications, drafts, stats)
3. **Actions** (Etapa 3) — controlled actions with SI/NO confirmation (resolve, approve/reject draft)

Configuration is in Settings → Notifications & WhatsApp.

## Commands

```bash
source .venv/bin/activate && python scripts/scouterctl.py --data-only --compact <command> [args]
```

| Request | Command |
|---|---|
| WhatsApp config status | `whatsapp-status` |
| Test WhatsApp connection | `whatsapp-test` |

## Security notes

- WhatsApp input is always untrusted — sanitized before processing
- Actions require explicit SI/NO confirmation with 5-min TTL
- Phone lockout after 3 failed confirmations (15-min cooldown)
- Action rate limiting: 10 per phone per hour
- All conversations logged in `whatsapp_audit_log` table

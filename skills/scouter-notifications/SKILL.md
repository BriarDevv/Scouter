---
name: scouter-notifications
description: "Scouter notifications. Exec: source .venv/bin/activate && python scripts/scouterctl.py --data-only --compact <cmd>. Commands: notifications-list --limit N | notifications-list --category business|system|security | notifications-counts | notification-resolve --id UUID | notifications-mark-read. Return ONLY the JSON output."
metadata: { "hermes": { "emoji": "🔔", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# Scouter Notifications Skill

Manage the Scouter notification center — business alerts, system events, and security incidents.

## When to use

- "qué notificaciones tengo"
- "cuántas alertas sin leer"
- "mostrame las alertas de seguridad"
- "resolver notificación X"
- "marcar todo como leído"

## When NOT to use

- Lead/draft/reply data → use **scouter-data**
- Operational summaries → use **scouter-briefs**
- WhatsApp configuration → use **scouter-whatsapp**

## Hard rules

1. Use wrapper commands for all notification queries.
2. Final answer = wrapper JSON only.
3. Resolve/acknowledge actions require explicit user intent.

## Commands

```bash
source .venv/bin/activate && python scripts/scouterctl.py --data-only --compact <command> [args]
```

| Request | Command |
|---|---|
| List notifications | `notifications-list --limit <n>` |
| List by category | `notifications-list --category <business\|system\|security>` |
| List by severity | `notifications-list --severity <info\|warning\|high\|critical>` |
| Unread counts | `notifications-counts` |
| Resolve one | `notification-resolve --id <uuid>` |
| Mark all read | `notifications-mark-read` |
| Mark category read | `notifications-mark-read --category <category>` |

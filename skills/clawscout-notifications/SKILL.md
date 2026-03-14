---
name: clawscout-notifications
description: "Query, manage, and resolve ClawScout notifications and security alerts. Covers in-app and WhatsApp alert channels."
metadata: { "openclaw": { "emoji": "🔔", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Notifications Skill

Manage the ClawScout notification center — business alerts, system events, and security incidents.

## When to use

- "qué notificaciones tengo"
- "cuántas alertas sin leer"
- "mostrame las alertas de seguridad"
- "resolver notificación X"
- "marcar todo como leído"

## When NOT to use

- Lead/draft/reply data → use **clawscout-data**
- Operational summaries → use **clawscout-briefs**
- WhatsApp configuration → use **clawscout-whatsapp**

## Hard rules

1. Use wrapper commands for all notification queries.
2. Final answer = wrapper JSON only.
3. Resolve/acknowledge actions require explicit user intent.

## Commands

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact <command> [args]
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

# Scouter Skills Registry

**Last updated:** 2026-04-03
**Source:** Agent OS Audit

---

## Mote Skills (7)

Skills are documented in `skills/*/SKILL.md` and define Mote's operational capabilities.

| Skill | Purpose | Mutating? | Model Used | Source |
|---|---|---|---|---|
| `scouter-data` | Exact grounded data (counts, IDs, statuses, lists) | No | None (tool-only) | `skills/scouter-data/SKILL.md` |
| `scouter-briefs` | Operational briefs with leader summarization | No | Leader (4b) | `skills/scouter-briefs/SKILL.md` |
| `scouter-actions` | Mutating operations (drafts, pipelines, reviews) | **Yes** | Executor (9b) / Reviewer (27b) | `skills/scouter-actions/SKILL.md` |
| `scouter-mail` | Send approved drafts, check delivery status | No | None | `skills/scouter-mail/SKILL.md` |
| `scouter-browser` | Read-only website inspection via Playwright | No | None | `skills/scouter-browser/SKILL.md` |
| `scouter-notifications` | Notification center management | Yes (resolve) | None | `skills/scouter-notifications/SKILL.md` |
| `scouter-whatsapp` | WhatsApp integration status and config | No | None | `skills/scouter-whatsapp/SKILL.md` |

Model routing rules: `skills/MODEL_ROUTING.md`

---

## Mote Tools (55)

### Tools Requiring Confirmation (22)

| Tool | Category | What It Does |
|---|---|---|
| `create_lead` | Leads | Create a new lead record |
| `update_lead_status` | Leads | Change lead lifecycle status |
| `generate_draft` | Outreach | Generate email outreach draft (LLM) |
| `approve_draft` | Outreach | Approve draft for sending |
| `reject_draft` | Outreach | Reject draft with feedback |
| `send_draft` | Outreach | Send approved email via SMTP |
| `generate_whatsapp_draft` | Outreach | Generate WhatsApp message (LLM) |
| `send_whatsapp_draft` | Outreach | Send WhatsApp via Kapso |
| `run_lead_research` | Research | Run web research on lead |
| `generate_commercial_brief` | Research | Generate opportunity brief (LLM) |
| `create_territory` | Territories | Create geographic territory |
| `update_territory` | Territories | Modify territory config |
| `delete_territory` | Territories | Remove territory |
| `add_to_suppression` | Suppression | Block email/domain |
| `remove_from_suppression` | Suppression | Unblock email/domain |
| `sync_inbound_mail` | Mail | Trigger IMAP fetch |
| `generate_reply_draft` | Replies | Generate reply to inbound (LLM) |
| `send_reply_draft` | Replies | Send reply via SMTP |
| `run_full_pipeline` | Pipeline | Start single-lead pipeline |
| `run_batch_pipeline` | Pipeline | Start batch pipeline |
| `start_territory_crawl` | Territories | Start Google Maps crawl |

### Tools Not Requiring Confirmation (33)

| Tool | Category | What It Does |
|---|---|---|
| `search_leads` | Leads | Search/filter leads |
| `get_lead_detail` | Leads | Full lead record |
| `count_leads_by_status` | Leads | Status distribution |
| `list_top_leads` | Leads | Top scoring leads |
| `list_drafts` | Outreach | List outreach drafts |
| `update_draft_content` | Outreach | Edit draft subject/body |
| `list_outreach_logs` | Outreach | Activity log |
| `get_lead_dossier` | Research | Research report |
| `get_commercial_brief` | Research | Commercial brief |
| `export_leads` | Research | CSV/JSON/XLSX export |
| `get_dashboard_stats` | Stats | Pipeline metrics |
| `get_pipeline_breakdown` | Stats | Stage distribution |
| `get_industry_breakdown` | Stats | Per-industry metrics |
| `get_city_breakdown` | Stats | Per-city metrics |
| `get_source_performance` | Stats | Per-source metrics |
| `get_time_series` | Stats | 30-day trends |
| `get_system_overview` | Stats | System summary |
| `get_reply_summary` | Stats | Inbound reply stats |
| `list_recent_activity` | Stats | Recent outreach activity |
| `list_notifications` | Notifications | Notification list |
| `mark_notification_read` | Notifications | Mark as read |
| `get_notification_counts` | Notifications | Unread counts |
| `list_inbound_messages` | Mail | Inbound messages |
| `classify_inbound_message` | Mail | Classify reply (LLM) |
| `list_suppression` | Suppression | Blocked list |
| `review_lead` | Reviews | Request lead review (LLM) |
| `review_draft` | Reviews | Request draft review (LLM) |
| `get_operational_settings` | Settings | Current config |
| `update_setting` | Settings | Modify whitelisted setting |
| `health_check` | System | System health |
| `get_current_time` | System | Server time |
| `get_pipeline_status` | Pipeline | Pipeline run status |
| `list_territories` | Territories | Territory list |
| `get_crawl_status` | Territories | Crawl progress |

---

## Analyst (Executor) Capabilities

The Analyst role has no formal "skills" today — it operates through 13 prompt definitions:

| Capability | Prompt ID | Output |
|---|---|---|
| Business summary | `BUSINESS_SUMMARY_PROMPT` | Text description |
| Lead quality evaluation | `LEAD_QUALITY_PROMPT` | quality + reasoning + angle |
| Email draft generation | `OUTREACH_DRAFT_PROMPT` | subject + body |
| WhatsApp draft generation | `WHATSAPP_DRAFT_PROMPT` | message text |
| Inbound reply classification | `INBOUND_REPLY_CLASSIFICATION_PROMPT` | label (10 categories) |
| Reply assistant draft | `REPLY_ASSISTANT_DRAFT_PROMPT` | response draft |
| Dossier generation | `DOSSIER_PROMPT` | structured business dossier |
| Commercial brief generation | `COMMERCIAL_BRIEF_PROMPT` | opportunity analysis |

---

## Reviewer Capabilities

| Capability | Prompt ID | Output |
|---|---|---|
| Lead review | `LEAD_REVIEW_PROMPT` | verdict + reasoning |
| Draft review | `OUTREACH_DRAFT_REVIEW_PROMPT` | verdict + tone + personalization |
| Inbound review | `INBOUND_REPLY_REVIEW_PROMPT` | verdict + escalation |
| Reply draft review | `REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT` | verdict |
| Brief review | `COMMERCIAL_BRIEF_REVIEW_PROMPT` | verdict |

---

## Coordinator (Leader) Capabilities

| Capability | Context | Output |
|---|---|---|
| Brief summarization | `scouter-briefs` skill only | Operational summary from grounded data |

---

## Skills That Should Exist (Future)

| Agent | Proposed Skill | Purpose |
|---|---|---|
| Analyst | `vertical-adaptation` | Adjust tone/angle based on industry patterns |
| Analyst | `contact-strategy` | Choose channel based on learned preferences |
| Reviewer | `common-corrections` | Track and surface repeated issues |
| Reviewer | `quality-benchmarking` | Compare draft quality over time |
| Coordinator | `daily-synthesis` | Produce operational summary reports |
| Coordinator | `trend-detection` | Surface significant metric changes |
| Mote | `system-evolution` | Review and approve agent improvement proposals |
| Mote | `operator-preferences` | Adapt to operator style from feedback |

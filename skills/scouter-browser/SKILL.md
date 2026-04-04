---
name: scouter-browser
description: "Inspect public business websites with Playwright through scripts/browserctl.py. Use this for grounded site checks such as title, meta description, h1, contact signals, CTA signals, social links, screenshots, or inspecting a lead's website by lead id."
metadata: { "hermes": { "emoji": "🌐", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# Scouter Browser Skill

Use this skill for safe, read-only inspection of public websites. This skill is grounded in `scripts/browserctl.py`, which uses Playwright and returns structured JSON.

Scouter remains the source of truth for lead state. This browser skill is for on-demand inspection only and does not write to the database.

## Use this skill for

- Inspecting a public URL to understand the visible site quality
- Checking if a site exposes contact signals, CTA signals, or social links
- Getting a screenshot for a public page when useful
- Inspecting a lead's current `website_url` through Scouter by lead id

## Do not use this skill for

- Logging in
- Filling or submitting forms
- Sending messages
- Clicking destructive actions
- Deep crawling or scraping many pages
- Any authenticated or private workflow

## Command map

Run commands from the Scouter workspace root:

```bash
python3 scripts/browserctl.py inspect-url --url <public_url>
python3 scripts/browserctl.py inspect-url --url <public_url> --screenshot
python3 scripts/browserctl.py inspect-business-site --lead-id <lead_id>
python3 scripts/browserctl.py inspect-business-site --lead-id <lead_id> --screenshot
```

## Grounding rules

- For website facts, use `browserctl` output and copy fields exactly from JSON.
- Do not invent contact methods, social links, CTA labels, or page-type guesses.
- If a field is missing or null in the JSON, say it is unavailable.
- When asked for exact output, return only the fields the user requested.
- Keep screenshots optional. Only request `--screenshot` when the user asks for a screenshot or when visual evidence adds value.

## Safety rules

- Stay on the provided public URL.
- Do not click, submit, authenticate, or navigate through flows that mutate state.
- If the site blocks access or times out, report the wrapper error plainly.

## Response rules

- Prefer compact JSON or short bullet summaries for inspection results.
- Highlight:
  - `final_url`
  - `title`
  - `meta_description`
  - `h1`
  - `contact_signals`
  - `cta_signals`
  - `social_links`
  - `page_type_guess`
  - `screenshot_path` when present

# Lead Scoring System

**Status:** Current as of 2026-04-04
**Implementation:** `app/scoring/rules.py`

## How Scoring Works

Rule-based scoring engine. Higher score = better prospect for web development services.

**Score range:** 0-100

### Score Breakdown (max 100)

| Category | Max Points | Source |
|----------|-----------|--------|
| Signals | 55 | Detected web presence problems |
| Industry | 15 | High-value industries bonus |
| Completeness | 12 | Contact info availability |
| Google Maps | 18 | Low rating + few reviews |

### Signal Weights

| Signal | Points | Meaning |
|--------|--------|---------|
| `no_website` | 30 | No website at all (strongest signal) |
| `instagram_only` | 25 | Only has Instagram, no web |
| `outdated_website` | 20 | Website exists but is outdated |
| `website_error` | 15 | Website returns errors |
| `no_custom_domain` | 15 | Using free domain |
| `no_mobile_friendly` | 12 | Not mobile responsive |
| `no_visible_email` | 10 | No email on website |
| `no_ssl` | 10 | No HTTPS |
| `weak_seo` | 8 | Poor SEO signals |
| `slow_load` | 8 | Slow page load |
| `has_website` | 0 | Neutral (not a penalty) |
| `has_custom_domain` | 0 | Neutral |

Signals cap at 55 points total.

### Industry Bonus

+15 points for high-value industries (restaurants, salons, gyms, clinics, real estate, etc.)

Full list in `HIGH_VALUE_INDUSTRIES` set in `app/scoring/rules.py`.

### Completeness Bonus

| Field | Points |
|-------|--------|
| Phone number | 3 |
| Email | 5 |
| Instagram | 2 |
| City | 2 |

### Score Thresholds

| Level | Range | Dashboard display |
|-------|-------|-------------------|
| High | >= 60 | Green |
| Medium | 30-59 | Amber |
| Low | < 30 | Red |

Defined in `dashboard/lib/constants.ts:SCORE_THRESHOLDS`.

## Outcome-Based Recommendations

When >= 50 outcomes (WON/LOST) accumulate, `outcome_analysis_service.py` generates scoring weight adjustment recommendations by comparing signal win rates to the average.

Recommendations are surfaced in:
- `/performance/recommendations` API endpoint
- Weekly synthesis reports
- AI Office dashboard

"""WhatsApp template selection based on lead signals.

Picks the best Meta-approved template for first contact based on
the lead's detected signals. Templates must be pre-created in the
Kapso panel and approved by Meta before use.

Template naming convention: apertura_{variant}
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateChoice:
    name: str
    language: str
    param_names: list[str]  # positional param descriptions for documentation


# ── Template registry ─────────────────────────────────────────────────
# These must match templates created in Kapso panel.
TEMPLATES = {
    "apertura_instagram": TemplateChoice(
        name="apertura_instagram",
        language="es_AR",
        param_names=["contact_name", "sender_name"],
    ),
    "apertura_sin_web": TemplateChoice(
        name="apertura_sin_web",
        language="es_AR",
        param_names=["contact_name", "business_name"],
    ),
    "apertura_web_vieja": TemplateChoice(
        name="apertura_web_vieja",
        language="es_AR",
        param_names=["contact_name", "business_name"],
    ),
    "apertura_general": TemplateChoice(
        name="apertura_general",
        language="es_AR",
        param_names=["contact_name", "sender_name"],
    ),
    "seguimiento": TemplateChoice(
        name="seguimiento",
        language="es_AR",
        param_names=["contact_name", "business_name"],
    ),
}

DEFAULT_TEMPLATE = "apertura_general"

# Signal sets that trigger specific templates
_INSTAGRAM_SIGNALS = {"instagram_only"}
_NO_WEBSITE_SIGNALS = {"no_website"}
_OUTDATED_SIGNALS = {"outdated_website", "no_ssl", "no_mobile_friendly"}


def select_template(signals: list[str]) -> TemplateChoice:
    """Select the best template based on lead signals.

    Priority:
    1. Instagram-only leads → apertura_instagram
    2. No website → apertura_sin_web
    3. Outdated/broken website → apertura_web_vieja
    4. Default → apertura_general
    """
    signal_set = set(signals) if signals else set()

    if signal_set & _INSTAGRAM_SIGNALS:
        return TEMPLATES["apertura_instagram"]
    if signal_set & _NO_WEBSITE_SIGNALS:
        return TEMPLATES["apertura_sin_web"]
    if signal_set & _OUTDATED_SIGNALS:
        return TEMPLATES["apertura_web_vieja"]
    return TEMPLATES[DEFAULT_TEMPLATE]


def build_template_parameters(
    template: TemplateChoice,
    contact_name: str,
    business_name: str,
    sender_name: str = "Scouter",
) -> list[dict]:
    """Build Kapso-compatible component parameters for a template.

    Maps param_names to actual values and returns the components array
    expected by the WhatsApp Cloud API.
    """
    value_map = {
        "contact_name": contact_name or business_name,
        "business_name": business_name,
        "sender_name": sender_name,
    }

    params = []
    for param_name in template.param_names:
        params.append(
            {
                "type": "text",
                "text": value_map.get(param_name, business_name),
            }
        )

    if not params:
        return []

    return [
        {
            "type": "body",
            "parameters": params,
        }
    ]

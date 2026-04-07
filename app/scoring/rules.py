"""Rule-based scoring engine for leads. Higher score = better prospect.

Score breakdown (max 100):
  Signals:        up to 55  (no_website 30 + instagram_only 25, OR website issues)
  Industry:       up to 15
  Completeness:   up to 12  (phone 3 + email 5 + instagram 2 + city 2)
  Google Maps:    up to 18  (low rating 8 + few reviews 10)
"""

from app.core.logging import get_logger
from app.models.lead import Lead
from app.models.lead_signal import SignalType

logger = get_logger(__name__)

# Signal weights: positive = good prospect for web dev services
SIGNAL_WEIGHTS: dict[SignalType, float] = {
    SignalType.NO_WEBSITE: 30.0,
    SignalType.INSTAGRAM_ONLY: 25.0,
    SignalType.OUTDATED_WEBSITE: 20.0,
    SignalType.NO_CUSTOM_DOMAIN: 15.0,
    SignalType.NO_VISIBLE_EMAIL: 10.0,
    SignalType.NO_SSL: 10.0,
    SignalType.WEAK_SEO: 8.0,
    SignalType.NO_MOBILE_FRIENDLY: 12.0,
    SignalType.SLOW_LOAD: 8.0,
    SignalType.WEBSITE_ERROR: 15.0,
    # Neutral: having a website is not a penalty — score comes from problems found
    SignalType.HAS_WEBSITE: 0.0,
    SignalType.HAS_CUSTOM_DOMAIN: 0.0,
}

# Industries with higher likelihood of needing web services
HIGH_VALUE_INDUSTRIES = {
    "restaurante",
    "restaurant",
    "gastronomia",
    "gastronomía",
    "peluqueria",
    "peluquería",
    "salon",
    "salón",
    "barberia",
    "barbería",
    "gimnasio",
    "gym",
    "fitness",
    "clinica",
    "clínica",
    "consultorio",
    "odontologia",
    "odontología",
    "inmobiliaria",
    "real estate",
    "estudio contable",
    "contador",
    "abogado",
    "estudio jurídico",
    "estudio juridico",
    "veterinaria",
    "hotel",
    "hostel",
    "alojamiento",
    "tienda",
    "shop",
    "boutique",
    "indumentaria",
    "taller",
    "mecanico",
    "mecánico",
    "floreria",
    "florería",
    "panaderia",
    "panadería",
    "confiteria",
    "confitería",
    "optica",
    "óptica",
    "libreria",
    "librería",
    "lavadero",
    "car wash",
    "ferreteria",
    "ferretería",
    "cafeteria",
    "cafetería",
    "café",
    "cafe",
    "bar",
}

INDUSTRY_BONUS = 15.0

# Data completeness bonuses
COMPLETENESS_BONUSES = {
    "has_phone": 3.0,
    "has_email": 5.0,
    "has_instagram": 2.0,
    "has_city": 2.0,
}


def _get_scoring_overrides(db=None) -> dict[str, float]:
    """Load scoring weight overrides from OperationalSettings if available."""
    if db is None:
        return {}
    try:
        from app.services.settings.operational_settings_service import get_cached_settings

        ops = get_cached_settings(db)
        return getattr(ops, "scoring_overrides", None) or {}
    except Exception as exc:
        logger.debug("scoring_overrides_unavailable", error=str(exc), exc_info=True)
        return {}


def compute_score(lead: Lead, db=None) -> float:
    """Compute a prospect score for a lead. Range: 0-100.

    If db is provided, reads scoring weight overrides from OperationalSettings
    (applied via batch review proposals).
    """
    score = 0.0
    overrides = _get_scoring_overrides(db)

    # Signal-based scoring (with optional overrides from proposals)
    for signal in lead.signals:
        signal_key = (
            signal.signal_type.value
            if hasattr(signal.signal_type, "value")
            else str(signal.signal_type)
        )
        if signal_key in overrides:
            score += overrides[signal_key]
        else:
            score += SIGNAL_WEIGHTS.get(signal.signal_type, 0.0)

    # Industry bonus
    if lead.industry:
        industry_lower = lead.industry.lower().strip()
        if industry_lower in HIGH_VALUE_INDUSTRIES:
            score += INDUSTRY_BONUS

    # Data completeness
    if lead.phone:
        score += COMPLETENESS_BONUSES["has_phone"]
    if lead.email:
        score += COMPLETENESS_BONUSES["has_email"]
    if lead.instagram_url:
        score += COMPLETENESS_BONUSES["has_instagram"]
    if lead.city:
        score += COMPLETENESS_BONUSES["has_city"]

    # Google Maps data bonuses — businesses with few reviews or low rating
    # are more likely to be small/local and need web services
    if lead.rating is not None and lead.rating < 4.0:
        score += 8.0
    if lead.review_count is not None:
        if lead.review_count < 10:
            score += 10.0
        elif lead.review_count < 50:
            score += 5.0

    # Clamp to 0-100
    return max(0.0, min(100.0, score))

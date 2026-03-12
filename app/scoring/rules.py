"""Rule-based scoring engine for leads. Higher score = better prospect."""

from app.models.lead import Lead
from app.models.lead_signal import SignalType

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
    # Negative signals (already has good web presence)
    SignalType.HAS_WEBSITE: -5.0,
    SignalType.HAS_CUSTOM_DOMAIN: -5.0,
}

# Industries with higher likelihood of needing web services
HIGH_VALUE_INDUSTRIES = {
    "restaurante", "restaurant", "gastronomia", "gastronomía",
    "peluqueria", "peluquería", "salon", "salón", "barberia", "barbería",
    "gimnasio", "gym", "fitness",
    "clinica", "clínica", "consultorio", "odontologia", "odontología",
    "inmobiliaria", "real estate",
    "estudio contable", "contador",
    "abogado", "estudio jurídico", "estudio juridico",
    "veterinaria",
    "hotel", "hostel", "alojamiento",
    "tienda", "shop", "boutique", "indumentaria",
    "taller", "mecanico", "mecánico",
}

INDUSTRY_BONUS = 10.0

# Data completeness bonuses
COMPLETENESS_BONUSES = {
    "has_phone": 3.0,
    "has_email": 5.0,
    "has_instagram": 2.0,
    "has_city": 2.0,
}


def compute_score(lead: Lead) -> float:
    """Compute a prospect score for a lead. Range: 0-100."""
    score = 0.0

    # Signal-based scoring
    for signal in lead.signals:
        weight = SIGNAL_WEIGHTS.get(signal.signal_type, 0.0)
        score += weight

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

    # Clamp to 0-100
    return max(0.0, min(100.0, score))

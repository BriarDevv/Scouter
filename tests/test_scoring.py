"""Tests for the scoring rules engine."""

from unittest.mock import MagicMock

from app.models.lead_signal import SignalType
from app.scoring.rules import compute_score


def _make_signal(signal_type: SignalType, detail: str = "") -> MagicMock:
    signal = MagicMock()
    signal.signal_type = signal_type
    signal.detail = detail
    return signal


def _make_lead(signals=None, industry=None, phone=None, email=None, instagram_url=None, city=None,
               rating=None, review_count=None):
    lead = MagicMock()
    lead.signals = signals or []
    lead.industry = industry
    lead.phone = phone
    lead.email = email
    lead.instagram_url = instagram_url
    lead.city = city
    lead.rating = rating
    lead.review_count = review_count
    return lead


def test_no_website_high_score():
    lead = _make_lead(
        signals=[_make_signal(SignalType.NO_WEBSITE)],
        industry="restaurante",
        city="Buenos Aires",
        phone="+5411123456",
    )
    score = compute_score(lead)
    assert score >= 40.0


def test_good_website_low_score():
    lead = _make_lead(
        signals=[
            _make_signal(SignalType.HAS_WEBSITE),
            _make_signal(SignalType.HAS_CUSTOM_DOMAIN),
        ],
    )
    score = compute_score(lead)
    assert score == 0.0  # Negative signals clamped to 0


def test_instagram_only_scores_well():
    lead = _make_lead(
        signals=[
            _make_signal(SignalType.NO_WEBSITE),
            _make_signal(SignalType.INSTAGRAM_ONLY),
        ],
        instagram_url="https://instagram.com/test",
        email="test@test.com",
    )
    score = compute_score(lead)
    assert score >= 50.0


def test_website_with_problems_scores_well():
    """A lead with a website that has issues should be a good prospect."""
    lead = _make_lead(
        signals=[
            _make_signal(SignalType.HAS_WEBSITE),
            _make_signal(SignalType.HAS_CUSTOM_DOMAIN),
            _make_signal(SignalType.NO_SSL),
            _make_signal(SignalType.WEAK_SEO),
            _make_signal(SignalType.NO_MOBILE_FRIENDLY),
        ],
        industry="restaurante",
        city="CABA",
    )
    score = compute_score(lead)
    # NO_SSL(10) + WEAK_SEO(8) + NO_MOBILE_FRIENDLY(12) + industry(15) + city(2) = 47
    assert score >= 40.0


def test_website_error_scores_like_prospect():
    """A lead whose website errors out is a good prospect."""
    lead = _make_lead(
        signals=[_make_signal(SignalType.WEBSITE_ERROR)],
        industry="clinica",
        city="CABA",
    )
    score = compute_score(lead)
    # WEBSITE_ERROR(15) + industry(15) + city(2) = 32
    assert score >= 25.0


def test_score_capped_at_100():
    # Stack all positive signals
    lead = _make_lead(
        signals=[
            _make_signal(SignalType.NO_WEBSITE),
            _make_signal(SignalType.INSTAGRAM_ONLY),
            _make_signal(SignalType.NO_CUSTOM_DOMAIN),
            _make_signal(SignalType.NO_VISIBLE_EMAIL),
            _make_signal(SignalType.NO_SSL),
            _make_signal(SignalType.WEAK_SEO),
            _make_signal(SignalType.NO_MOBILE_FRIENDLY),
            _make_signal(SignalType.SLOW_LOAD),
        ],
        industry="restaurante",
        phone="+54",
        email="a@b.com",
        instagram_url="https://instagram.com/x",
        city="CABA",
    )
    score = compute_score(lead)
    assert score == 100.0

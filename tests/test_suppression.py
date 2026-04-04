"""Tests for is_suppressed OR logic in lead_service."""

from app.models.suppression import SuppressionEntry
from app.services.leads.lead_service import is_suppressed


def test_suppressed_by_email(db):
    db.add(SuppressionEntry(email="blocked@example.com"))
    db.commit()

    assert is_suppressed(db, email="blocked@example.com") is True


def test_suppressed_by_domain(db):
    db.add(SuppressionEntry(domain="spammer.com"))
    db.commit()

    assert is_suppressed(db, email=None, domain="spammer.com") is True


def test_suppressed_by_email_or_domain(db):
    """OR logic: suppressed email should return True even with a clean domain."""
    db.add(SuppressionEntry(email="flagged@good.com"))
    db.commit()

    # email is suppressed; domain is not — result must still be True
    assert is_suppressed(db, email="flagged@good.com", domain="other.com") is True


def test_not_suppressed(db):
    assert is_suppressed(db, email="clean@example.com", domain="clean.com") is False

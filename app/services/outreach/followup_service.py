"""Follow-up detection for leads that were contacted but never replied.

Closes docs/roadmaps/post-hardening-plan.md Item 2. No outbound send is
performed here — the beat task emits operator notifications so the human
decides whether to follow up manually or escalate. Automation of the
actual follow-up send is a future roadmap item (cost + risk).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.inbound_mail import InboundMessage
from app.models.lead import Lead, LeadStatus

logger = get_logger(__name__)


def find_leads_needing_followup(db: Session, followup_days: int) -> list[Lead]:
    """Return leads that (a) are in status=CONTACTED, (b) were last updated
    more than `followup_days` days ago, and (c) have no InboundMessage on
    record.

    Reply status (REPLIED/MEETING/WON/LOST) is excluded by the CONTACTED
    filter — we only care about leads who went silent after first outreach.
    """
    if followup_days <= 0:
        return []

    cutoff = datetime.now(UTC) - timedelta(days=followup_days)
    no_inbound = ~select(InboundMessage.id).where(InboundMessage.lead_id == Lead.id).exists()
    stmt = select(Lead).where(
        and_(
            Lead.status == LeadStatus.CONTACTED,
            Lead.updated_at < cutoff,
            no_inbound,
        )
    )
    return list(db.execute(stmt).scalars().all())

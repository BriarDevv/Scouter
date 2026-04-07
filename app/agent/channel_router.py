"""Unified channel router for non-streaming channels (Telegram, WhatsApp).

Provides a synchronous wrapper around the async agent core that collects
all events and returns a plain-text response.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.core import run_agent_turn
from app.agent.events import (
    AgentError,
    ConfirmationRequired,
    TextDelta,
)
from app.core.logging import get_logger
from app.models.conversation import Conversation

logger = get_logger(__name__)

MAX_RESPONSE_LENGTH = {
    "telegram": 4096,
    "whatsapp": 1024,
    "web": 10000,
}


def _find_or_create_conversation(db: Session, channel: str, channel_id: str) -> Conversation:
    """Find the most recent active conversation, or create one.

    For telegram/whatsapp: joins the most recent active conversation
    (any channel) so messages sync to the web chat panel.
    For web: scoped to channel+channel_id as before.
    """
    if channel == "web":
        stmt = (
            select(Conversation)
            .where(
                Conversation.channel == "web",
                Conversation.channel_id == channel_id,
                Conversation.is_active.is_(True),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
    else:
        # Cross-channel sync: find ANY recent active conversation
        stmt = (
            select(Conversation)
            .where(Conversation.is_active.is_(True))
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
    conv = db.execute(stmt).scalar_one_or_none()
    if conv:
        return conv

    conv = Conversation(channel=channel, channel_id=channel_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    logger.info(
        "conversation_created_by_channel",
        channel=channel,
        channel_id=channel_id,
        conversation_id=str(conv.id),
    )
    return conv


def handle_channel_message(
    *,
    db: Session,
    channel: str,
    channel_id: str,
    message: str,
    attachments: list[dict] | None = None,
) -> str:
    """Synchronous entry point for non-streaming channels.

    Finds or creates a conversation, runs the agent to completion,
    and returns the full text response truncated to channel limits.
    """
    conv = _find_or_create_conversation(db, channel, channel_id)

    # Collect all events synchronously
    text_parts: list[str] = []
    confirmations: list[str] = []

    async def _collect_events() -> None:
        async for event in run_agent_turn(
            conversation_id=conv.id,
            user_message=message,
            db=db,
            channel=channel,
        ):
            if isinstance(event, TextDelta):
                text_parts.append(event.content)
            elif isinstance(event, ConfirmationRequired):
                confirmations.append(
                    f"⚠️ {event.description_es}\nRespondé SI para confirmar o NO para cancelar."
                )
            elif isinstance(event, AgentError):
                text_parts.append(f"\n❌ Error: {event.error}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in an async context — create a new task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_collect_events())).result()
        else:
            loop.run_until_complete(_collect_events())
    except RuntimeError:
        asyncio.run(_collect_events())

    # Build response
    if confirmations:
        response = "\n\n".join(confirmations)
    else:
        response = "".join(text_parts).strip()

    if not response:
        response = "No pude procesar tu mensaje. Intentá de nuevo."

    # Truncate to channel limit
    max_len = MAX_RESPONSE_LENGTH.get(channel, 4096)
    if len(response) > max_len:
        response = response[: max_len - 3] + "..."

    return response

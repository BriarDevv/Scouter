import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.conversation import Conversation, Message

logger = get_logger(__name__)


def create_conversation(
    db: Session, *, channel: str = "web", channel_id: str | None = None
) -> Conversation:
    conv = Conversation(channel=channel, channel_id=channel_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    logger.info("conversation_created", conversation_id=str(conv.id), channel=channel)
    return conv


def get_conversation(db: Session, conversation_id: uuid.UUID) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def list_conversations(
    db: Session, *, channel: str | None = None, limit: int = 20
) -> list[dict]:
    stmt = select(Conversation).where(Conversation.is_active == True)  # noqa: E712
    if channel:
        stmt = stmt.where(Conversation.channel == channel)
    stmt = stmt.order_by(Conversation.updated_at.desc()).limit(limit)
    conversations = db.execute(stmt).scalars().all()

    result = []
    for conv in conversations:
        msg_count = db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conv.id)
        ).scalar_one()
        last_msg = db.execute(
            select(func.max(Message.created_at)).where(
                Message.conversation_id == conv.id
            )
        ).scalar()
        result.append({
            "id": conv.id,
            "title": conv.title,
            "message_count": msg_count,
            "last_message_at": last_msg,
            "created_at": conv.created_at,
        })
    return result


def delete_conversation(db: Session, conversation_id: uuid.UUID) -> bool:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        return False
    conv.is_active = False
    db.commit()
    return True


def get_messages(
    db: Session, conversation_id: uuid.UUID, *, limit: int = 100
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def generate_title(first_message: str) -> str:
    """Generate a conversation title from the first message."""
    clean = first_message.strip()
    if len(clean) <= 40:
        return clean
    return clean[:37] + "..."


def update_conversation_title(
    db: Session, conversation_id: uuid.UUID, title: str
) -> None:
    conv = db.get(Conversation, conversation_id)
    if conv and not conv.title:
        conv.title = title
        db.commit()

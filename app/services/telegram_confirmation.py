"""Telegram confirmation system -- pending action storage with TTL.

Actions via Telegram require explicit confirmation before execution.
Flow: user sends command -> pending stored (5 min TTL) -> user confirms SI/NO.

Separate state from WhatsApp confirmation — keyed by chat_id.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)

_TTL_SECONDS = 300  # 5 minutes
_LOCKOUT_SECONDS = 900  # 15 minutes
_MAX_FAILED_CONFIRMATIONS = 3


@dataclass
class PendingAction:
    id: str
    chat_id: str
    intent: str
    params: dict
    created_at: datetime
    description_es: str


# -- In-memory state (resets on restart) --
_pending: dict[str, PendingAction] = {}  # keyed by chat_id

# Failed confirmation tracking: chat_id -> list of timestamps
_failed_confirmations: dict[str, list[float]] = defaultdict(list)

# Lockout tracking: chat_id -> lockout_expires_at timestamp
_lockouts: dict[str, float] = {}


def create_pending(
    chat_id: str,
    intent: str,
    params: dict,
    description_es: str,
) -> str:
    """Store a pending action and return a confirmation prompt message."""
    cleanup_expired()

    action = PendingAction(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        intent=intent,
        params=params,
        created_at=datetime.now(timezone.utc),
        description_es=description_es,
    )
    _pending[chat_id] = action
    logger.info(
        "tg_pending_created",
        chat_id=chat_id[:6] + "***",
        intent=intent,
        action_id=action.id,
    )
    return (
        "Confirmar: " + description_es + "?\n"
        "Responde *SI* para confirmar o *NO* para cancelar."
    )


def confirm_pending(chat_id: str) -> PendingAction | None:
    """Return and remove the pending action for a chat, or None if expired/missing."""
    cleanup_expired()
    action = _pending.pop(chat_id, None)
    if action is not None:
        _failed_confirmations.pop(chat_id, None)
        logger.info(
            "tg_pending_confirmed",
            chat_id=chat_id[:6] + "***",
            intent=action.intent,
            action_id=action.id,
        )
    return action


def cancel_pending(chat_id: str) -> bool:
    """Cancel the pending action for a chat. Returns True if there was one."""
    action = _pending.pop(chat_id, None)
    if action is not None:
        logger.info(
            "tg_pending_cancelled",
            chat_id=chat_id[:6] + "***",
            intent=action.intent,
            action_id=action.id,
        )
        return True
    return False


def has_pending(chat_id: str) -> bool:
    """Check if chat has a pending action (not expired)."""
    cleanup_expired()
    return chat_id in _pending


def cleanup_expired() -> None:
    """Remove actions older than TTL."""
    now = datetime.now(timezone.utc)
    expired = [
        cid
        for cid, action in _pending.items()
        if (now - action.created_at).total_seconds() > _TTL_SECONDS
    ]
    for cid in expired:
        action = _pending.pop(cid)
        logger.info(
            "tg_pending_expired",
            chat_id=cid[:6] + "***",
            intent=action.intent,
            action_id=action.id,
        )


def record_failed_confirmation(chat_id: str) -> bool:
    """Record a failed confirmation attempt. Returns True if chat is now locked."""
    now = time.time()
    _failed_confirmations[chat_id] = [
        t for t in _failed_confirmations[chat_id]
        if now - t < _LOCKOUT_SECONDS
    ]
    _failed_confirmations[chat_id].append(now)

    if len(_failed_confirmations[chat_id]) >= _MAX_FAILED_CONFIRMATIONS:
        _lockouts[chat_id] = now + _LOCKOUT_SECONDS
        _failed_confirmations.pop(chat_id, None)
        logger.warning(
            "tg_chat_locked",
            chat_id=chat_id[:6] + "***",
            lockout_minutes=_LOCKOUT_SECONDS // 60,
        )
        return True
    return False


def is_locked(chat_id: str) -> bool:
    """Check if a chat is locked out from actions."""
    lockout_until = _lockouts.get(chat_id)
    if lockout_until is None:
        return False
    if time.time() >= lockout_until:
        _lockouts.pop(chat_id, None)
        return False
    return True


# -- Test helpers --

def _reset_state() -> None:
    """Clear all in-memory state (for tests)."""
    _pending.clear()
    _failed_confirmations.clear()
    _lockouts.clear()

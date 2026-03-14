"""WhatsApp confirmation system -- pending action storage with TTL.

Actions via WhatsApp require explicit confirmation before execution.
Flow: user sends command -> pending stored (5 min TTL) -> user confirms SI/NO.
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
    phone: str
    intent: str
    params: dict
    created_at: datetime
    description_es: str


# -- In-memory state (resets on restart) --
_pending: dict[str, PendingAction] = {}  # keyed by phone

# Failed confirmation tracking: phone -> list of timestamps
_failed_confirmations: dict[str, list[float]] = defaultdict(list)

# Lockout tracking: phone -> lockout_expires_at timestamp
_lockouts: dict[str, float] = {}


def create_pending(
    phone: str,
    intent: str,
    params: dict,
    description_es: str,
) -> str:
    """Store a pending action and return a confirmation prompt message."""
    cleanup_expired()

    action = PendingAction(
        id=str(uuid.uuid4()),
        phone=phone,
        intent=intent,
        params=params,
        created_at=datetime.now(timezone.utc),
        description_es=description_es,
    )
    _pending[phone] = action
    logger.info(
        "wa_pending_created",
        phone=phone[:6] + "***",
        intent=intent,
        action_id=action.id,
    )
    return (
        "Confirmar: " + description_es + "?\n"
        "Responde *SI* para confirmar o *NO* para cancelar."
    )


def confirm_pending(phone: str) -> PendingAction | None:
    """Return and remove the pending action for a phone, or None if expired/missing."""
    cleanup_expired()
    action = _pending.pop(phone, None)
    if action is not None:
        # Clear failed confirmations on success
        _failed_confirmations.pop(phone, None)
        logger.info(
            "wa_pending_confirmed",
            phone=phone[:6] + "***",
            intent=action.intent,
            action_id=action.id,
        )
    return action


def cancel_pending(phone: str) -> bool:
    """Cancel the pending action for a phone. Returns True if there was one."""
    action = _pending.pop(phone, None)
    if action is not None:
        logger.info(
            "wa_pending_cancelled",
            phone=phone[:6] + "***",
            intent=action.intent,
            action_id=action.id,
        )
        return True
    return False


def has_pending(phone: str) -> bool:
    """Check if phone has a pending action (not expired)."""
    cleanup_expired()
    return phone in _pending


def cleanup_expired() -> None:
    """Remove actions older than TTL."""
    now = datetime.now(timezone.utc)
    expired = [
        phone
        for phone, action in _pending.items()
        if (now - action.created_at).total_seconds() > _TTL_SECONDS
    ]
    for phone in expired:
        action = _pending.pop(phone)
        logger.info(
            "wa_pending_expired",
            phone=phone[:6] + "***",
            intent=action.intent,
            action_id=action.id,
        )


def record_failed_confirmation(phone: str) -> bool:
    """Record a failed confirmation attempt. Returns True if phone is now locked."""
    now = time.time()
    # Prune old failures (outside lockout window)
    _failed_confirmations[phone] = [
        t for t in _failed_confirmations[phone]
        if now - t < _LOCKOUT_SECONDS
    ]
    _failed_confirmations[phone].append(now)

    if len(_failed_confirmations[phone]) >= _MAX_FAILED_CONFIRMATIONS:
        _lockouts[phone] = now + _LOCKOUT_SECONDS
        _failed_confirmations.pop(phone, None)
        logger.warning(
            "wa_phone_locked",
            phone=phone[:6] + "***",
            lockout_minutes=_LOCKOUT_SECONDS // 60,
        )
        return True
    return False


def is_locked(phone: str) -> bool:
    """Check if a phone is locked out from actions."""
    lockout_until = _lockouts.get(phone)
    if lockout_until is None:
        return False
    if time.time() >= lockout_until:
        _lockouts.pop(phone, None)
        return False
    return True


# -- Test helpers --


def _reset_state() -> None:
    """Clear all in-memory state (for tests)."""
    _pending.clear()
    _failed_confirmations.clear()
    _lockouts.clear()

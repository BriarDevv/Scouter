"""Suppression domain — email/domain/phone suppression list."""

from app.services.suppression.suppression_service import (
    add_to_suppression_list,
    list_suppression,
    remove_from_suppression,
)

__all__ = [
    "add_to_suppression_list",
    "list_suppression",
    "remove_from_suppression",
]

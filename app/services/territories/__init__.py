"""Territories domain — geographic territory CRUD and stats."""

from app.services.territories.territory_service import (
    create_territory,
    delete_territory,
    get_all_territories_with_stats,
    get_territory,
    get_territory_stats,
    get_territory_with_stats,
    list_territories,
    update_territory,
)

__all__ = [
    "create_territory",
    "delete_territory",
    "get_all_territories_with_stats",
    "get_territory",
    "get_territory_stats",
    "get_territory_with_stats",
    "list_territories",
    "update_territory",
]

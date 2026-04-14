"""Growth Intelligence domain — adjacency lookups and performance tracking.

The Growth Agent relies on these services to discover expansion opportunities
(nearby cities, similar cities) and to evaluate how existing territories and
niches perform over time.
"""

from app.services.growth.adjacency import (
    get_cities_by_similarity,
    get_cities_in_province,
    get_uncovered_cities,
)
from app.services.growth.growth_service import (
    execute_growth_decision,
    get_growth_state,
    run_growth_cycle,
)
from app.services.growth.performance_service import (
    get_all_territory_performance,
    get_category_performance,
    get_territory_performance,
    snapshot_territory_performance,
)

__all__ = [
    "execute_growth_decision",
    "get_all_territory_performance",
    "get_category_performance",
    "get_cities_by_similarity",
    "get_cities_in_province",
    "get_growth_state",
    "get_territory_performance",
    "get_uncovered_cities",
    "run_growth_cycle",
    "snapshot_territory_performance",
]

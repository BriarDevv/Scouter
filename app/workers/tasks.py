"""Backward-compatible re-exports -- tasks have moved to domain files.

Import from the specific module (e.g. app.workers.pipeline_tasks) for new code.
"""

from app.workers.batch_tasks import (  # noqa: F401
    task_batch_pipeline,
    task_rescore_all,
)
from app.workers.crawl_tasks import task_crawl_territory  # noqa: F401
from app.workers.pipeline_tasks import (  # noqa: F401
    _should_generate_draft,
    _track_failure,
    task_analyze_lead,
    task_enrich_lead,
    task_full_pipeline,
    task_generate_draft,
    task_score_lead,
)
from app.workers.research_tasks import task_research_lead  # noqa: F401
from app.workers.review_tasks import (  # noqa: F401
    task_review_draft,
    task_review_inbound_message,
    task_review_lead,
    task_review_reply_assistant_draft,
)

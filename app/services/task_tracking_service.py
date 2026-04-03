import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task_tracking import PipelineRun, TaskRun

logger = get_logger(__name__)

TASK_PROGRESS_STATUSES = {"running", "retrying", "stopping", "stopped", "succeeded", "failed"}
ACTIVE_TASK_RUN_STATUSES = ("queued", "running", "retrying", "stopping")


def utcnow() -> datetime:
    return datetime.now(UTC)


def bind_tracking_context(
    *,
    lead_id: str | None = None,
    task_id: str | None = None,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
    current_step: str | None = None,
) -> None:
    structlog.contextvars.bind_contextvars(
        lead_id=lead_id,
        task_id=task_id,
        pipeline_run_id=pipeline_run_id,
        correlation_id=correlation_id,
        current_step=current_step,
    )


def clear_tracking_context() -> None:
    structlog.contextvars.clear_contextvars()


def create_pipeline_run(
    db: Session,
    lead_id: uuid.UUID,
    *,
    current_step: str = "pipeline_dispatch",
    correlation_id: str | None = None,
) -> PipelineRun:
    pipeline_run = PipelineRun(
        lead_id=lead_id,
        correlation_id=correlation_id or str(uuid.uuid4()),
        status="queued",
        current_step=current_step,
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)
    logger.info(
        "pipeline_run_created",
        pipeline_run_id=str(pipeline_run.id),
        lead_id=str(lead_id),
        correlation_id=pipeline_run.correlation_id,
        current_step=current_step,
    )
    return pipeline_run


def attach_pipeline_root_task(
    db: Session,
    pipeline_run_id: uuid.UUID,
    root_task_id: str,
) -> PipelineRun | None:
    pipeline_run = db.get(PipelineRun, pipeline_run_id)
    if not pipeline_run:
        return None
    pipeline_run.root_task_id = root_task_id
    db.commit()
    db.refresh(pipeline_run)
    return pipeline_run


def queue_task_run(
    db: Session,
    *,
    task_id: str,
    task_name: str,
    queue: str | None,
    lead_id: uuid.UUID | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
    scope_key: str | None = None,
    current_step: str | None = None,
) -> TaskRun:
    def _apply_metadata(task_run: TaskRun, *, preserve_progress: bool) -> None:
        task_run.task_name = task_name
        task_run.queue = queue
        task_run.lead_id = lead_id
        task_run.pipeline_run_id = pipeline_run_id
        task_run.correlation_id = correlation_id
        task_run.scope_key = scope_key

        if preserve_progress and task_run.status in TASK_PROGRESS_STATUSES:
            task_run.current_step = task_run.current_step or current_step
            return

        task_run.status = "queued"
        task_run.current_step = current_step
        task_run.error = None

    task_run = db.get(TaskRun, task_id)
    is_new = task_run is None
    if not task_run:
        task_run = TaskRun(task_id=task_id, task_name=task_name)
        db.add(task_run)

    _apply_metadata(task_run, preserve_progress=not is_new)

    try:
        db.commit()
    except IntegrityError:
        # A fast worker may persist the task before the API finishes writing
        # its own queued row. Reload and keep the most advanced state.
        db.rollback()
        task_run = db.get(TaskRun, task_id)
        if not task_run:
            raise
        _apply_metadata(task_run, preserve_progress=True)
        db.commit()

    db.refresh(task_run)
    logger.info(
        "task_run_synced" if task_run.status != "queued" else "task_run_queued",
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        lead_id=str(lead_id) if lead_id else None,
        pipeline_run_id=str(pipeline_run_id) if pipeline_run_id else None,
        scope_key=scope_key,
        current_step=current_step,
    )
    return task_run


def mark_task_running(
    db: Session,
    *,
    task_id: str,
    task_name: str,
    queue: str | None,
    lead_id: uuid.UUID | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
    scope_key: str | None = None,
    current_step: str | None = None,
) -> TaskRun:
    task_run = queue_task_run(
        db,
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        lead_id=lead_id,
        pipeline_run_id=pipeline_run_id,
        correlation_id=correlation_id,
        scope_key=scope_key,
        current_step=current_step,
    )
    task_run.status = "running"
    task_run.started_at = task_run.started_at or utcnow()

    if pipeline_run_id:
        update_pipeline_run(
            db,
            pipeline_run_id,
            status="running",
            current_step=current_step,
            started=True,
            clear_error=True,
            commit=False,
        )

    db.commit()
    db.refresh(task_run)

    logger.info(
        "task_run_started",
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        current_step=current_step,
    )
    return task_run


def mark_task_succeeded(
    db: Session,
    *,
    task_id: str,
    result: dict | None = None,
    current_step: str | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    pipeline_status: str | None = None,
) -> TaskRun | None:
    task_run = db.get(TaskRun, task_id)
    if not task_run:
        return None
    task_run.status = "succeeded"
    task_run.current_step = current_step or task_run.current_step
    task_run.result = result
    task_run.error = None
    task_run.finished_at = utcnow()

    if pipeline_run_id:
        update_pipeline_run(
            db,
            pipeline_run_id,
            status=pipeline_status or "running",
            current_step=current_step,
            result=result if pipeline_status == "succeeded" else None,
            clear_error=True,
            finished=pipeline_status == "succeeded",
            commit=False,
        )

    db.commit()
    db.refresh(task_run)

    logger.info("task_run_succeeded", task_id=task_id, current_step=current_step, result=result)
    return task_run


def mark_task_retrying(
    db: Session,
    *,
    task_id: str,
    error: str,
    current_step: str | None = None,
    pipeline_run_id: uuid.UUID | None = None,
) -> TaskRun | None:
    task_run = db.get(TaskRun, task_id)
    if not task_run:
        return None
    task_run.status = "retrying"
    task_run.current_step = current_step or task_run.current_step
    task_run.error = error

    if pipeline_run_id:
        update_pipeline_run(
            db,
            pipeline_run_id,
            status="running",
            current_step=current_step,
            error=f"Retry scheduled: {error}",
            commit=False,
        )

    db.commit()
    db.refresh(task_run)

    logger.warning("task_run_retrying", task_id=task_id, current_step=current_step, error=error)
    return task_run


def mark_task_failed(
    db: Session,
    *,
    task_id: str,
    error: str,
    current_step: str | None = None,
    pipeline_run_id: uuid.UUID | None = None,
) -> TaskRun | None:
    task_run = db.get(TaskRun, task_id)
    if not task_run:
        return None
    task_run.status = "failed"
    task_run.current_step = current_step or task_run.current_step
    task_run.error = error
    task_run.finished_at = utcnow()

    if pipeline_run_id:
        update_pipeline_run(
            db,
            pipeline_run_id,
            status="failed",
            current_step=current_step,
            error=error,
            finished=True,
            commit=False,
        )

    db.commit()
    db.refresh(task_run)

    logger.error("task_run_failed", task_id=task_id, current_step=current_step, error=error)
    return task_run


def update_task_run(
    db: Session,
    task_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    progress_json: dict | None = None,
    result: dict | None = None,
    error: str | None = None,
    clear_error: bool = False,
    started: bool = False,
    finished: bool = False,
    stop_requested: bool | None = None,
    commit: bool = True,
) -> TaskRun | None:
    task_run = db.get(TaskRun, task_id)
    if not task_run:
        return None
    if status is not None:
        task_run.status = status
    if current_step is not None:
        task_run.current_step = current_step
    if progress_json is not None:
        task_run.progress_json = progress_json
    if result is not None:
        task_run.result = result
    if error is not None:
        task_run.error = error
    elif clear_error:
        task_run.error = None
    if started and task_run.started_at is None:
        task_run.started_at = utcnow()
    if finished:
        task_run.finished_at = utcnow()
    if stop_requested is True:
        task_run.stop_requested_at = task_run.stop_requested_at or utcnow()
    elif stop_requested is False:
        task_run.stop_requested_at = None
    if commit:
        db.commit()
        db.refresh(task_run)
    logger.info(
        "task_run_updated",
        task_id=task_id,
        status=task_run.status,
        current_step=task_run.current_step,
        scope_key=task_run.scope_key,
    )
    return task_run


def update_pipeline_run(
    db: Session,
    pipeline_run_id: uuid.UUID,
    *,
    status: str | None = None,
    current_step: str | None = None,
    result: dict | None = None,
    error: str | None = None,
    clear_error: bool = False,
    started: bool = False,
    finished: bool = False,
    commit: bool = True,
) -> PipelineRun | None:
    pipeline_run = db.get(PipelineRun, pipeline_run_id)
    if not pipeline_run:
        return None
    if status is not None:
        pipeline_run.status = status
    if current_step is not None:
        pipeline_run.current_step = current_step
    if result is not None:
        pipeline_run.result = result
    if error is not None:
        pipeline_run.error = error
    elif clear_error:
        pipeline_run.error = None
    if started and pipeline_run.started_at is None:
        pipeline_run.started_at = utcnow()
    if finished:
        pipeline_run.finished_at = utcnow()
    if commit:
        db.commit()
        db.refresh(pipeline_run)
    logger.info(
        "pipeline_run_updated",
        pipeline_run_id=str(pipeline_run.id),
        status=pipeline_run.status,
        current_step=pipeline_run.current_step,
        error=pipeline_run.error,
    )
    return pipeline_run


def get_task_run(db: Session, task_id: str) -> TaskRun | None:
    return db.get(TaskRun, task_id)


def is_task_stop_requested(db: Session, task_id: str) -> bool:
    task_run = db.get(TaskRun, task_id)
    return bool(task_run and task_run.stop_requested_at is not None)


def get_scoped_task_run(
    db: Session,
    *,
    task_name: str,
    scope_key: str,
    active_only: bool = False,
) -> TaskRun | None:
    stmt = (
        select(TaskRun)
        .where(TaskRun.task_name == task_name, TaskRun.scope_key == scope_key)
        .order_by(TaskRun.created_at.desc())
        .limit(1)
    )
    if active_only:
        stmt = stmt.where(TaskRun.status.in_(ACTIVE_TASK_RUN_STATUSES))
    return db.execute(stmt).scalars().first()


def request_task_stop(
    db: Session,
    *,
    task_name: str,
    scope_key: str,
) -> TaskRun | None:
    task_run = get_scoped_task_run(db, task_name=task_name, scope_key=scope_key, active_only=True)
    if not task_run:
        return None
    task_run.status = "stopping"
    task_run.stop_requested_at = task_run.stop_requested_at or utcnow()
    db.commit()
    db.refresh(task_run)
    logger.info(
        "task_run_stop_requested",
        task_id=task_run.task_id,
        task_name=task_run.task_name,
        scope_key=task_run.scope_key,
        current_step=task_run.current_step,
    )
    return task_run


def list_task_runs(
    db: Session,
    *,
    status: str | None = None,
    lead_id: uuid.UUID | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    scope_key: str | None = None,
    limit: int = 20,
) -> list[TaskRun]:
    stmt = select(TaskRun)
    if status:
        stmt = stmt.where(TaskRun.status == status)
    if lead_id:
        stmt = stmt.where(TaskRun.lead_id == lead_id)
    if pipeline_run_id:
        stmt = stmt.where(TaskRun.pipeline_run_id == pipeline_run_id)
    if scope_key:
        stmt = stmt.where(TaskRun.scope_key == scope_key)
    stmt = stmt.order_by(TaskRun.updated_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_pipeline_runs(
    db: Session,
    *,
    lead_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[PipelineRun]:
    stmt = select(PipelineRun)
    if lead_id:
        stmt = stmt.where(PipelineRun.lead_id == lead_id)
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    stmt = stmt.order_by(PipelineRun.updated_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_pipeline_run(db: Session, pipeline_run_id: uuid.UUID) -> PipelineRun | None:
    return db.get(PipelineRun, pipeline_run_id)

"""Pipeline tools — run pipelines and check status."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.pipeline.task_tracking_service import (
    get_pipeline_run,
    list_pipeline_runs,
)


def run_full_pipeline(db: Session, *, lead_id: str) -> dict:
    """Run the full enrichment pipeline for a lead."""
    from app.services.pipeline.task_tracking_service import create_pipeline_run, queue_task_run
    from app.workers.tasks import task_enrich_lead

    try:
        lead_uuid = uuid.UUID(lead_id)
    except ValueError:
        return {"error": "ID de lead inválido"}
    pipeline_run = create_pipeline_run(db, lead_id=lead_uuid)
    task = task_enrich_lead.delay(
        lead_id, str(pipeline_run.id), pipeline_run.correlation_id
    )
    queue_task_run(
        db,
        task_id=str(task.id),
        task_name="task_enrich_lead",
        queue="enrichment",
        lead_id=lead_uuid,
        pipeline_run_id=pipeline_run.id,
        correlation_id=pipeline_run.correlation_id,
    )
    db.commit()
    return {
        "pipeline_run_id": str(pipeline_run.id),
        "correlation_id": pipeline_run.correlation_id,
        "status": "queued",
        "message": f"Pipeline iniciado para lead {lead_id}",
    }


def run_batch_pipeline(db: Session) -> dict:
    """Run batch pipeline for all new leads."""
    from app.models.lead import Lead, LeadStatus
    from sqlalchemy import select

    new_leads = db.execute(
        select(Lead.id).where(Lead.status == LeadStatus.NEW).limit(50)
    ).scalars().all()

    if not new_leads:
        return {"message": "No hay leads nuevos para procesar", "count": 0}

    from app.services.pipeline.task_tracking_service import create_pipeline_run, queue_task_run
    from app.workers.tasks import task_enrich_lead

    started = 0
    for lead_id in new_leads:
        pipeline_run = create_pipeline_run(db, lead_id=lead_id)
        task = task_enrich_lead.delay(
            str(lead_id), str(pipeline_run.id), pipeline_run.correlation_id
        )
        queue_task_run(
            db,
            task_id=str(task.id),
            task_name="task_enrich_lead",
            queue="enrichment",
            lead_id=lead_id,
            pipeline_run_id=pipeline_run.id,
            correlation_id=pipeline_run.correlation_id,
        )
        started += 1

    db.commit()
    return {"message": f"Pipeline batch iniciado para {started} leads", "count": started}


def get_pipeline_status(
    db: Session, *, pipeline_run_id: str | None = None, limit: int = 5
) -> dict:
    """Get pipeline run status."""
    if pipeline_run_id:
        try:
            rid = uuid.UUID(pipeline_run_id)
        except ValueError:
            return {"error": "ID de pipeline run inválido"}
        run = get_pipeline_run(db, rid)
        if not run:
            return {"error": "Pipeline run no encontrado"}
        return {
            "id": str(run.id),
            "lead_id": str(run.lead_id),
            "status": run.status,
            "current_step": run.current_step,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error": run.error,
        }

    runs = list_pipeline_runs(db, limit=min(limit, 20))
    return {
        "count": len(runs),
        "runs": [
            {
                "id": str(r.id),
                "lead_id": str(r.lead_id),
                "status": r.status,
                "current_step": r.current_step,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
    }


registry.register(ToolDefinition(
    name="run_full_pipeline",
    description="Ejecutar el pipeline completo de enriquecimiento para un lead (requiere confirmación)",
    parameters=[
        ToolParameter("lead_id", "string", "UUID del lead"),
    ],
    category="pipeline",
    requires_confirmation=True,
    handler=run_full_pipeline,
))

registry.register(ToolDefinition(
    name="run_batch_pipeline",
    description="Ejecutar pipeline batch para todos los leads nuevos (requiere confirmación)",
    category="pipeline",
    requires_confirmation=True,
    handler=run_batch_pipeline,
))

registry.register(ToolDefinition(
    name="get_pipeline_status",
    description="Ver el estado de un pipeline run o listar los últimos runs",
    parameters=[
        ToolParameter("pipeline_run_id", "string", "UUID del pipeline run", required=False),
        ToolParameter("limit", "integer", "Cantidad de runs recientes (default 5)", required=False),
    ],
    category="pipeline",
    handler=get_pipeline_status,
))

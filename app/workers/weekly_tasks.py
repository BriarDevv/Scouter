"""Weekly Celery tasks — AI team synthesis and reporting.

Generates a weekly report aggregating corrections, outcomes, metrics,
and produces recommendations. Optionally uses LLM for natural language synthesis.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.weekly_tasks.task_weekly_report")
def task_weekly_report():
    """Generate weekly AI team report with metrics, patterns, and recommendations.

    Scheduled via Celery Beat (Sunday 20:00 Argentina time).
    Can also be triggered manually via API or Mote tool.
    """
    now = datetime.now(UTC)
    week_end = now
    week_start = now - timedelta(days=7)

    logger.info(
        "weekly_report_starting", week_start=week_start.isoformat(), week_end=week_end.isoformat()
    )

    try:
        with SessionLocal() as db:
            metrics = _collect_metrics(db, week_start, week_end)
            recommendations = _collect_recommendations(db)
            synthesis = _generate_synthesis(db, metrics, recommendations)

            from app.models.weekly_report import WeeklyReport

            report = WeeklyReport(
                week_start=week_start,
                week_end=week_end,
                metrics_json=metrics,
                recommendations_json=recommendations,
                synthesis_text=synthesis["text"],
                synthesis_model=synthesis.get("model"),
            )
            db.add(report)
            db.commit()

            logger.info(
                "weekly_report_generated",
                report_id=str(report.id),
                metrics_keys=list(metrics.keys()),
                recommendations_count=len(recommendations),
                has_synthesis=bool(synthesis["text"]),
            )

            # Notify operator
            try:
                from app.services.notifications.notification_emitter import emit_notification

                emit_notification(
                    db,
                    category="system",
                    severity="info",
                    title="Reporte semanal del equipo IA listo",
                    message=f"Semana {week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}: "
                    f"{metrics.get('leads_processed', 0)} leads, "
                    f"{metrics.get('won', 0)} WON, "
                    f"{len(recommendations)} recomendaciones.",
                    source="weekly_report",
                )
            except Exception:
                logger.debug("weekly_report_notification_failed", exc_info=True)

            return {"status": "ok", "report_id": str(report.id)}

    except Exception as exc:
        logger.error("weekly_report_failed", error=str(exc))
        return {"status": "failed", "error": str(exc)}


def _collect_metrics(db, week_start: datetime, week_end: datetime) -> dict:
    """Collect all metrics for the weekly report."""
    from sqlalchemy import func, select

    from app.models.investigation_thread import InvestigationThread
    from app.models.lead import Lead
    from app.models.llm_invocation import LLMInvocation
    from app.models.outcome_snapshot import OutcomeSnapshot
    from app.models.outreach import OutreachDraft
    from app.models.review_correction import ReviewCorrection

    # Leads
    leads_processed = (
        db.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= week_start, Lead.created_at < week_end
            )
        ).scalar()
        or 0
    )

    high_leads = (
        db.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= week_start, Lead.llm_quality == "high"
            )
        ).scalar()
        or 0
    )

    # Outcomes
    won = (
        db.execute(
            select(func.count(OutcomeSnapshot.id)).where(
                OutcomeSnapshot.created_at >= week_start, OutcomeSnapshot.outcome == "won"
            )
        ).scalar()
        or 0
    )

    lost = (
        db.execute(
            select(func.count(OutcomeSnapshot.id)).where(
                OutcomeSnapshot.created_at >= week_start, OutcomeSnapshot.outcome == "lost"
            )
        ).scalar()
        or 0
    )

    # Drafts
    drafts_generated = (
        db.execute(
            select(func.count(OutreachDraft.id)).where(OutreachDraft.generated_at >= week_start)
        ).scalar()
        or 0
    )

    # Invocations
    executor_calls = (
        db.execute(
            select(func.count(LLMInvocation.id)).where(
                LLMInvocation.created_at >= week_start, LLMInvocation.role == "executor"
            )
        ).scalar()
        or 0
    )

    reviewer_calls = (
        db.execute(
            select(func.count(LLMInvocation.id)).where(
                LLMInvocation.created_at >= week_start, LLMInvocation.role == "reviewer"
            )
        ).scalar()
        or 0
    )

    fallback_count = (
        db.execute(
            select(func.count(LLMInvocation.id)).where(
                LLMInvocation.created_at >= week_start, LLMInvocation.fallback_used.is_(True)
            )
        ).scalar()
        or 0
    )

    # Corrections
    corrections_count = (
        db.execute(
            select(func.count(ReviewCorrection.id)).where(ReviewCorrection.created_at >= week_start)
        ).scalar()
        or 0
    )

    # Scout investigations
    investigations = (
        db.execute(
            select(func.count(InvestigationThread.id)).where(
                InvestigationThread.created_at >= week_start
            )
        ).scalar()
        or 0
    )

    total_invocations = executor_calls + reviewer_calls
    return {
        "period": f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
        "leads_processed": leads_processed,
        "high_leads": high_leads,
        "won": won,
        "lost": lost,
        "drafts_generated": drafts_generated,
        "executor_calls": executor_calls,
        "reviewer_calls": reviewer_calls,
        "fallback_rate": round(fallback_count / max(total_invocations, 1), 2),
        "corrections_count": corrections_count,
        "scout_investigations": investigations,
    }


def _collect_recommendations(db) -> list[dict]:
    """Collect recommendations from outcome analysis."""
    try:
        from app.services.pipeline.outcome_analysis_service import generate_scoring_recommendations

        return generate_scoring_recommendations(db)
    except Exception as exc:
        logger.warning("recommendations_collection_failed", error=str(exc))
        return []


def _generate_synthesis(db, metrics: dict, recommendations: list[dict]) -> dict:
    """Generate natural language synthesis via LLM (or fallback to template)."""
    # Try LLM synthesis
    try:
        from app.llm.client import invoke_text
        from app.llm.roles import LLMRole

        prompt = _build_synthesis_prompt(metrics, recommendations)
        result = invoke_text(
            function_name="weekly_report_synthesis",
            prompt_id="weekly_synthesis",
            prompt_version="v1",
            system_prompt=(
                "Sos el coordinador del equipo IA de Scouter. "
                "Genera un resumen semanal corto y accionable en español rioplatense. "
                "Mencioná los números clave, qué funcionó, qué no, y qué recomendás. "
                "Máximo 300 palabras. Sé directo."
            ),
            user_prompt=prompt,
            role=LLMRole.EXECUTOR,
            persist=False,
        )
        if result.text:
            return {"text": result.text, "model": result.model}
    except Exception as exc:
        logger.warning("llm_synthesis_failed_using_template", error=str(exc))

    # Fallback: template synthesis
    text = _template_synthesis(metrics, recommendations)
    return {"text": text, "model": None}


def _build_synthesis_prompt(metrics: dict, recommendations: list[dict]) -> str:
    """Build the user prompt for LLM synthesis."""
    rec_text = "\n".join(
        f"- [{r.get('type', '?')}] {r.get('description', '')}: {r.get('action', '')}"
        for r in recommendations[:5]
    )
    return f"""Datos de la semana:
- Leads procesados: {metrics["leads_processed"]}
- Leads HIGH: {metrics["high_leads"]}
- WON: {metrics["won"]}, LOST: {metrics["lost"]}
- Drafts generados: {metrics["drafts_generated"]}
- Executor calls: {metrics["executor_calls"]}, Reviewer calls: {metrics["reviewer_calls"]}
- Fallback rate: {metrics["fallback_rate"]:.0%}
- Correcciones del reviewer: {metrics["corrections_count"]}
- Investigaciones de Scout: {metrics["scout_investigations"]}

Recomendaciones del sistema:
{rec_text or "Sin recomendaciones esta semana."}

Generá el resumen semanal."""


def _template_synthesis(metrics: dict, recommendations: list[dict]) -> str:
    """Fallback template when LLM is unavailable."""
    parts = [
        f"Semana {metrics['period']}:",
        f"- {metrics['leads_processed']} leads procesados, {metrics['high_leads']} HIGH",
        f"- {metrics['won']} WON, {metrics['lost']} LOST",
        f"- {metrics['drafts_generated']} drafts generados",
        f"- {metrics['scout_investigations']} investigaciones de Scout",
        f"- {metrics['corrections_count']} correcciones del reviewer",
        f"- Fallback rate: {metrics['fallback_rate']:.0%}",
    ]
    if recommendations:
        parts.append("\nRecomendaciones:")
        for r in recommendations[:3]:
            parts.append(f"- {r.get('description', '')}")
    return "\n".join(parts)

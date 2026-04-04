from datetime import datetime, timedelta, timezone
import uuid

from app.models.inbound_mail import EmailThread, InboundMailClassificationStatus, InboundMessage
from app.models.lead import Lead, LeadStatus
from app.models.lead_source import LeadSource, SourceType
from app.models.outreach import DraftStatus, LogAction, OutreachDraft, OutreachLog
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus
from app.models.task_tracking import PipelineRun, TaskRun


def seed_leader_data(db):
    now = datetime.now(timezone.utc)

    crawler = LeadSource(name="Crawler BA", source_type=SourceType.CRAWLER)
    manual = LeadSource(name="Manual Ops", source_type=SourceType.MANUAL)
    db.add_all([crawler, manual])
    db.flush()

    leads = [
        Lead(
            business_name="Atlas AI",
            industry="Tech",
            city="CABA",
            score=91,
            status=LeadStatus.WON,
            source_id=crawler.id,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(hours=1),
        ),
        Lead(
            business_name="Beacon Foods",
            industry="Retail",
            city="Rosario",
            score=72,
            status=LeadStatus.QUALIFIED,
            source_id=crawler.id,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(hours=2),
        ),
        Lead(
            business_name="Cometa Health",
            industry="Health",
            city="CABA",
            score=65,
            status=LeadStatus.DRAFT_READY,
            source_id=manual.id,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=3),
        ),
        Lead(
            business_name="Delta Services",
            industry="Services",
            city="Mendoza",
            score=44,
            status=LeadStatus.CONTACTED,
            source_id=manual.id,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=4),
        ),
        Lead(
            business_name="Echo Retail",
            industry="Retail",
            city="Rosario",
            score=18,
            status=LeadStatus.NEW,
            source_id=crawler.id,
            created_at=now - timedelta(hours=12),
            updated_at=now - timedelta(hours=5),
        ),
    ]
    db.add_all(leads)
    db.flush()

    pending_draft = OutreachDraft(
        lead_id=leads[2].id,
        subject="Draft ready for review",
        body="Draft body",
        status=DraftStatus.PENDING_REVIEW,
        generated_at=now - timedelta(hours=2),
    )
    approved_draft = OutreachDraft(
        lead_id=leads[3].id,
        subject="Approved draft",
        body="Approved body",
        status=DraftStatus.APPROVED,
        generated_at=now - timedelta(hours=5),
        reviewed_at=now - timedelta(hours=4),
    )
    db.add_all([pending_draft, approved_draft])
    db.flush()

    running_pipeline = PipelineRun(
        id=uuid.uuid4(),
        lead_id=leads[3].id,
        correlation_id="corr-running",
        root_task_id="task-full-running",
        status="running",
        current_step="analysis",
        created_at=now - timedelta(hours=3),
        updated_at=now - timedelta(minutes=20),
        started_at=now - timedelta(hours=3),
    )
    failed_pipeline = PipelineRun(
        id=uuid.uuid4(),
        lead_id=leads[4].id,
        correlation_id="corr-failed",
        root_task_id="task-full-failed",
        status="failed",
        current_step="scoring",
        error="score timeout",
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=5),
        started_at=now - timedelta(hours=6),
        finished_at=now - timedelta(hours=5),
    )
    db.add_all([running_pipeline, failed_pipeline])
    db.flush()

    db.add_all(
        [
            TaskRun(
                task_id="task-analyze-running",
                task_name="task_analyze_lead",
                queue="llm",
                lead_id=leads[3].id,
                pipeline_run_id=running_pipeline.id,
                correlation_id=running_pipeline.correlation_id,
                status="running",
                current_step="analysis",
                started_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=10),
            ),
            TaskRun(
                task_id="task-enrich-retrying",
                task_name="task_enrich_lead",
                queue="enrichment",
                lead_id=leads[2].id,
                correlation_id="corr-retrying",
                status="retrying",
                current_step="enrichment",
                error="temporary fetch error",
                started_at=now - timedelta(hours=2),
                updated_at=now - timedelta(minutes=30),
            ),
            TaskRun(
                task_id="task-score-failed",
                task_name="task_score_lead",
                queue="scoring",
                lead_id=leads[4].id,
                pipeline_run_id=failed_pipeline.id,
                correlation_id=failed_pipeline.correlation_id,
                status="failed",
                current_step="scoring",
                error="score timeout",
                started_at=now - timedelta(hours=6),
                updated_at=now - timedelta(hours=5),
                finished_at=now - timedelta(hours=5),
            ),
        ]
    )

    db.add_all(
        [
            OutreachLog(
                lead_id=leads[2].id,
                draft_id=pending_draft.id,
                action=LogAction.GENERATED,
                actor="system",
                detail="Draft generated",
                created_at=now - timedelta(hours=2),
            ),
            OutreachLog(
                lead_id=leads[3].id,
                draft_id=approved_draft.id,
                action=LogAction.APPROVED,
                actor="user",
                detail="Ready to send",
                created_at=now - timedelta(hours=4),
            ),
            OutreachLog(
                lead_id=leads[0].id,
                draft_id=None,
                action=LogAction.WON,
                actor="user",
                detail="Closed deal",
                created_at=now - timedelta(hours=6),
            ),
        ]
    )

    approved_delivery = OutreachDelivery(
        lead_id=leads[3].id,
        draft_id=approved_draft.id,
        provider="smtp",
        provider_message_id="smtp-message-123",
        recipient_email="owner@delta.example",
        subject_snapshot=approved_draft.subject,
        status=OutreachDeliveryStatus.SENT,
        sent_at=now - timedelta(hours=3),
    )
    db.add(approved_delivery)
    db.flush()

    thread = EmailThread(
        lead_id=leads[3].id,
        draft_id=approved_draft.id,
        delivery_id=approved_delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        external_thread_id="thread-123",
        thread_key="thread-123",
        matched_via="message_id",
        match_confidence=1.0,
        last_message_at=now - timedelta(minutes=45),
    )
    db.add(thread)
    db.flush()

    db.add_all(
        [
            InboundMessage(
                dedupe_key="imap:INBOX:reply-1",
                thread_id=thread.id,
                lead_id=leads[3].id,
                draft_id=approved_draft.id,
                delivery_id=approved_delivery.id,
                provider="imap",
                provider_mailbox="INBOX",
                provider_message_id="reply-1",
                message_id="<reply-1@example.com>",
                in_reply_to="<smtp-message-123>",
                from_email="owner@delta.example",
                to_email="sales@scouter.local",
                subject="Re: Approved draft",
                body_text="Nos interesa, pasen propuesta.",
                body_snippet="Nos interesa, pasen propuesta.",
                received_at=now - timedelta(minutes=45),
                classification_status=InboundMailClassificationStatus.CLASSIFIED.value,
                classification_label="asked_for_quote",
                summary="Pidieron propuesta comercial.",
                confidence=0.92,
                next_action_suggestion="Responder con presupuesto inicial.",
                should_escalate_reviewer=False,
                classification_role="executor",
                classification_model="qwen3.5:9b",
                classified_at=now - timedelta(minutes=40),
            ),
            InboundMessage(
                dedupe_key="imap:INBOX:reply-2",
                thread_id=thread.id,
                lead_id=leads[2].id,
                draft_id=pending_draft.id,
                provider="imap",
                provider_mailbox="INBOX",
                provider_message_id="reply-2",
                message_id="<reply-2@example.com>",
                from_email="ops@unknown.example",
                to_email="sales@scouter.local",
                subject="Re: Draft ready for review",
                body_text="Quiero hablar, pero el mensaje es ambiguo.",
                body_snippet="Quiero hablar, pero el mensaje es ambiguo.",
                received_at=now - timedelta(minutes=30),
                classification_status=InboundMailClassificationStatus.CLASSIFIED.value,
                classification_label="needs_human_review",
                summary="Respuesta ambigua con intención potencial.",
                confidence=0.31,
                next_action_suggestion="Revisar antes de responder.",
                should_escalate_reviewer=True,
                classification_role="executor",
                classification_model="qwen3.5:9b",
                classified_at=now - timedelta(minutes=25),
            ),
            InboundMessage(
                dedupe_key="imap:INBOX:reply-3",
                provider="imap",
                provider_mailbox="INBOX",
                provider_message_id="reply-3",
                message_id="<reply-3@example.com>",
                from_email="noreply@example.com",
                to_email="sales@scouter.local",
                subject="Out of office",
                body_text="Estoy fuera de la oficina hasta el lunes.",
                body_snippet="Estoy fuera de la oficina hasta el lunes.",
                received_at=now - timedelta(minutes=10),
                classification_status=InboundMailClassificationStatus.PENDING.value,
            ),
        ]
    )
    db.commit()


def test_leader_overview_and_top_leads(client, db):
    seed_leader_data(db)

    overview_resp = client.get("/api/v1/leader/overview")
    assert overview_resp.status_code == 200
    overview = overview_resp.json()
    assert overview["total_leads"] == 5
    assert overview["qualified"] == 4
    assert overview["avg_score"] == 58.0
    assert overview["drafts_pending_review"] == 1
    assert overview["drafts_approved"] == 1
    assert overview["pipelines_running"] == 1
    assert overview["pipelines_failed"] == 1
    assert overview["running_tasks"] == 1
    assert overview["retrying_tasks"] == 1
    assert overview["failed_tasks"] == 1
    assert overview["recent_activity_24h"] == 3
    assert overview["performance_highlights"]["top_industry"] == "Tech"
    assert overview["performance_highlights"]["top_city"] == "CABA"
    assert overview["performance_highlights"]["top_source"] == "Crawler BA"

    top_resp = client.get("/api/v1/leader/top-leads?limit=2")
    assert top_resp.status_code == 200
    top_leads = top_resp.json()
    assert [item["business_name"] for item in top_leads] == ["Atlas AI", "Beacon Foods"]
    assert [item["quality"] for item in top_leads] == ["high", "high"]

    filtered_resp = client.get("/api/v1/leader/top-leads?status=qualified")
    assert filtered_resp.status_code == 200
    filtered = filtered_resp.json()
    assert len(filtered) == 1
    assert filtered[0]["business_name"] == "Beacon Foods"


def test_leader_recent_drafts_pipelines_and_activity(client, db):
    seed_leader_data(db)

    drafts_resp = client.get("/api/v1/leader/recent-drafts?limit=5")
    assert drafts_resp.status_code == 200
    drafts = drafts_resp.json()
    assert drafts[0]["lead_name"] == "Cometa Health"
    assert drafts[0]["status"] == "pending_review"
    assert drafts[1]["lead_name"] == "Delta Services"

    pipeline_resp = client.get("/api/v1/leader/recent-pipelines?limit=5")
    assert pipeline_resp.status_code == 200
    pipelines = pipeline_resp.json()
    assert pipelines[0]["lead_name"] == "Delta Services"
    assert pipelines[0]["status"] == "running"
    assert pipelines[1]["lead_name"] == "Echo Retail"
    assert pipelines[1]["status"] == "failed"

    activity_resp = client.get("/api/v1/leader/activity?limit=5")
    assert activity_resp.status_code == 200
    activity = activity_resp.json()
    assert len(activity) == 3
    assert {item["lead_name"] for item in activity} == {"Atlas AI", "Cometa Health", "Delta Services"}


def test_leader_task_health(client, db):
    seed_leader_data(db)

    health_resp = client.get("/api/v1/leader/task-health?limit=5")
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["running_count"] == 1
    assert health["retrying_count"] == 1
    assert health["failed_count"] == 1
    assert health["running"][0]["task_id"] == "task-analyze-running"
    assert health["retrying"][0]["task_id"] == "task-enrich-retrying"
    assert health["failed"][0]["task_id"] == "task-score-failed"


def test_leader_reply_summary_and_lists(client, db):
    seed_leader_data(db)

    summary_resp = client.get("/api/v1/leader/replies/summary?hours=24")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_recent_replies"] == 3
    assert summary["replied_leads"] == 2
    assert summary["positive_replies"] == 1
    assert summary["quote_replies"] == 1
    assert summary["meeting_replies"] == 0
    assert summary["reviewer_candidates"] == 1
    assert summary["important_replies"] == 3
    assert summary["pending_classification"] == 1
    assert summary["failed_classification"] == 0
    assert summary["unmatched_replies"] == 1

    recent_resp = client.get("/api/v1/leader/replies?limit=5&hours=24")
    assert recent_resp.status_code == 200
    recent = recent_resp.json()
    assert len(recent) == 3
    assert recent[0]["classification_status"] == "pending"

    important_resp = client.get("/api/v1/leader/replies?important_only=true&limit=5&hours=24")
    assert important_resp.status_code == 200
    important = important_resp.json()
    assert [item["classification_label"] for item in important[:2]] == [
        "asked_for_quote",
        "needs_human_review",
    ]

    reviewer_resp = client.get("/api/v1/leader/replies?needs_reviewer=true&limit=5&hours=24")
    assert reviewer_resp.status_code == 200
    reviewer_items = reviewer_resp.json()
    assert len(reviewer_items) == 1
    assert reviewer_items[0]["classification_label"] == "needs_human_review"

    quote_resp = client.get("/api/v1/leader/replies?labels=asked_for_quote&limit=5&hours=24")
    assert quote_resp.status_code == 200
    quote_items = quote_resp.json()
    assert len(quote_items) == 1
    assert quote_items[0]["lead_name"] == "Delta Services"

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import (
    LeadCreate,
    LeadDetailResponse,
    LeadListResponse,
    LeadNameResponse,
    LeadResponse,
    LeadStatusUpdate,
)
from app.schemas.research import ResearchReportResponse
from app.services.leads.lead_service import (
    create_lead,
    get_lead,
    list_lead_names,
    list_leads,
    query_leads_for_export,
    update_lead_status,
)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=201)
def create(data: LeadCreate, db: Session = Depends(get_db)):
    """Create a new lead. Deduplicates automatically."""
    try:
        lead = create_lead(db, data)
        db.commit()
        return lead
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("", response_model=LeadListResponse)
def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: LeadStatus | None = None,
    min_score: float | None = None,
    db: Session = Depends(get_db),
):
    """List leads with pagination and optional filters."""
    leads, total = list_leads(
        db, page=page, page_size=page_size, status=status, min_score=min_score
    )
    return LeadListResponse(items=leads, total=total, page=page, page_size=page_size)


@router.get("/export")
def export_leads(
    format: str = "csv",
    status: str | None = None,
    quality: str | None = None,
    db: Session = Depends(get_db),
):
    """Export leads as CSV, JSON, or XLSX."""
    from app.services.research.export_service import (
        export_leads_csv,
        export_leads_json,
        export_leads_xlsx,
    )

    leads = query_leads_for_export(db, status=status, quality=quality)

    if format == "json":
        data = export_leads_json(leads)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=leads.json"},
        )
    elif format == "xlsx":
        data = export_leads_xlsx(leads)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads.xlsx"},
        )
    else:
        data = export_leads_csv(leads)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=leads.csv"},
        )


@router.get("/names", response_model=list[LeadNameResponse])
def list_names(
    limit: int = Query(5000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Return a lightweight list of {id, business_name} for all leads."""
    rows = list_lead_names(db, limit=limit)
    return [LeadNameResponse(id=row.id, business_name=row.business_name) for row in rows]


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_by_id(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a lead by ID with all signals."""
    lead = get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadDetailResponse.model_validate(lead)


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def patch_status(
    lead_id: uuid.UUID,
    data: LeadStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update the current pipeline status for a lead."""
    lead = update_lead_status(db, lead_id, data.status)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.commit()
    return lead


@router.get("/{lead_id}/timeline")
def get_lead_timeline(
    lead_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return the immutable LeadEvent timeline for a lead, ordered newest first."""
    from sqlalchemy import func, select

    from app.models.lead_event import LeadEvent
    from app.schemas.lead_event import LeadEventListOut, LeadEventOut

    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    total = db.execute(
        select(func.count()).select_from(LeadEvent).where(LeadEvent.lead_id == lead_id)
    ).scalar_one()
    rows = (
        db.execute(
            select(LeadEvent)
            .where(LeadEvent.lead_id == lead_id)
            .order_by(LeadEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return LeadEventListOut(
        items=[LeadEventOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{lead_id}/research", response_model=ResearchReportResponse)
def get_research_report(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get research report for a lead."""
    from app.services.research.research_service import get_research_report_for_lead

    report = get_research_report_for_lead(db, lead_id)
    if report is None:
        # Distinguish lead-not-found from report-not-found
        lead = get_lead(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        raise HTTPException(status_code=404, detail="Research report not found")
    return ResearchReportResponse.model_validate(report)


@router.post("/{lead_id}/research", response_model=ResearchReportResponse, status_code=201)
def trigger_research(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Trigger research for a lead. Runs synchronously."""
    from app.services.research.research_service import run_research

    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    report = run_research(db, lead_id)
    if not report:
        raise HTTPException(status_code=500, detail="Research failed")
    return ResearchReportResponse.model_validate(report)


@router.get("/{lead_id}/screenshot", response_class=FileResponse)
def get_lead_screenshot(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Serve the screenshot image for a lead."""
    from pathlib import Path

    from app.services.research.research_service import get_lead_screenshot_artifact

    lead, artifact = get_lead_screenshot_artifact(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not artifact:
        raise HTTPException(status_code=404, detail="No screenshot available")

    # Security: resolve symlinks and verify path is within storage directory
    storage_root = Path(__file__).resolve().parent.parent.parent / "storage"
    resolved = Path(artifact.file_path).resolve()
    if not resolved.is_relative_to(storage_root):
        raise HTTPException(status_code=403, detail="Invalid screenshot path")

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Screenshot file not found")

    return FileResponse(str(resolved), media_type="image/png")

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lead import Lead, LeadStatus
from app.models.research_report import LeadResearchReport
from app.schemas.lead import (
    LeadCreate,
    LeadDetailResponse,
    LeadListResponse,
    LeadNameResponse,
    LeadResponse,
    LeadStatusUpdate,
)
from app.schemas.research import ResearchReportResponse
from app.services.leads.lead_service import create_lead, get_lead, list_leads, update_lead_status

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=201)
def create(data: LeadCreate, db: Session = Depends(get_db)):
    """Create a new lead. Deduplicates automatically."""
    try:
        lead = create_lead(db, data)
        db.commit()
        return lead
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


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

    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    if quality:
        query = query.filter(Lead.llm_quality == quality)
    leads = query.order_by(Lead.created_at.desc()).yield_per(100)

    if format == "json":
        data = export_leads_json(db, leads)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=leads.json"},
        )
    elif format == "xlsx":
        data = export_leads_xlsx(db, leads)
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads.xlsx"},
        )
    else:
        data = export_leads_csv(db, leads)
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
    rows = db.query(Lead.id, Lead.business_name).order_by(Lead.business_name).limit(limit).all()
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


@router.get("/{lead_id}/research", response_model=ResearchReportResponse)
def get_research_report(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get research report for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    report = db.query(LeadResearchReport).filter_by(lead_id=lead_id).first()
    if not report:
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

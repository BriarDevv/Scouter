"""Export service -- CSV/JSON/XLSX export for leads."""

import csv
import io
import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead

logger = get_logger(__name__)


def export_leads_csv(db: Session, leads: list[Lead]) -> bytes:
    """Export leads as CSV bytes."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "business_name",
            "industry",
            "city",
            "website_url",
            "instagram_url",
            "email",
            "phone",
            "status",
            "score",
            "llm_quality",
            "created_at",
        ]
    )
    for lead in leads:
        writer.writerow(
            [
                str(lead.id),
                lead.business_name,
                lead.industry,
                lead.city,
                lead.website_url,
                lead.instagram_url,
                lead.email,
                lead.phone,
                lead.status.value if lead.status else "",
                lead.score,
                lead.llm_quality,
                lead.created_at.isoformat() if lead.created_at else "",
            ]
        )
    return output.getvalue().encode("utf-8")


def export_leads_json(db: Session, leads: list[Lead]) -> bytes:
    """Export leads as JSON bytes."""
    data = []
    for lead in leads:
        data.append(
            {
                "id": str(lead.id),
                "business_name": lead.business_name,
                "industry": lead.industry,
                "city": lead.city,
                "website_url": lead.website_url,
                "instagram_url": lead.instagram_url,
                "email": lead.email,
                "phone": lead.phone,
                "status": lead.status.value if lead.status else None,
                "score": lead.score,
                "llm_quality": lead.llm_quality,
                "llm_summary": lead.llm_summary,
                "llm_suggested_angle": lead.llm_suggested_angle,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            }
        )
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def export_leads_xlsx(db: Session, leads: list[Lead]) -> bytes:
    """Export leads as XLSX bytes."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    headers = [
        "ID",
        "Negocio",
        "Industria",
        "Ciudad",
        "Website",
        "Instagram",
        "Email",
        "Telefono",
        "Estado",
        "Score",
        "Calidad IA",
        "Creado",
    ]
    ws.append(headers)
    for lead in leads:
        ws.append(
            [
                str(lead.id),
                lead.business_name,
                lead.industry,
                lead.city,
                lead.website_url,
                lead.instagram_url,
                lead.email,
                lead.phone,
                lead.status.value if lead.status else "",
                lead.score,
                lead.llm_quality,
                lead.created_at.isoformat() if lead.created_at else "",
            ]
        )
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

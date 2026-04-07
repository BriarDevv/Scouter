import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ArtifactType(str, enum.Enum):
    SCREENSHOT = "screenshot"
    DOSSIER_PDF = "dossier_pdf"
    EXPORT = "export"
    BRIEF = "brief"


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="artifacts")  # noqa: F821

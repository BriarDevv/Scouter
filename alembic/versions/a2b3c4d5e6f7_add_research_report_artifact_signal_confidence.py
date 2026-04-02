"""add research report, artifact tables and signal confidence fields

Revision ID: a2b3c4d5e6f7
Revises: f7a8b9c0d1e2
Create Date: 2026-04-02 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- lead_research_reports ------------------------------------------------
    op.create_table(
        "lead_research_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="researchstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("website_exists", sa.Boolean(), nullable=True),
        sa.Column("website_url_verified", sa.Text(), nullable=True),
        sa.Column(
            "website_confidence",
            sa.Enum(
                "confirmed", "probable", "unknown", "mismatch",
                name="confidencelevel",
            ),
            nullable=True,
        ),
        sa.Column("instagram_exists", sa.Boolean(), nullable=True),
        sa.Column("instagram_url_verified", sa.Text(), nullable=True),
        sa.Column(
            "instagram_confidence",
            sa.Enum(
                "confirmed", "probable", "unknown", "mismatch",
                name="confidencelevel",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("whatsapp_detected", sa.Boolean(), nullable=True),
        sa.Column(
            "whatsapp_confidence",
            sa.Enum(
                "confirmed", "probable", "unknown", "mismatch",
                name="confidencelevel",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("screenshots_json", sa.JSON(), nullable=True),
        sa.Column("detected_signals_json", sa.JSON(), nullable=True),
        sa.Column("html_metadata_json", sa.JSON(), nullable=True),
        sa.Column("business_description", sa.Text(), nullable=True),
        sa.Column("researcher_model", sa.String(100), nullable=True),
        sa.Column("research_duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # -- artifacts ------------------------------------------------------------
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_type",
            sa.Enum(
                "screenshot", "dossier_pdf", "export", "brief",
                name="artifacttype",
            ),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_artifacts_lead_id", "artifacts", ["lead_id"])

    # -- lead_signals: add confidence + source columns ------------------------
    op.add_column(
        "lead_signals",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "lead_signals",
        sa.Column("source", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lead_signals", "source")
    op.drop_column("lead_signals", "confidence")
    op.drop_index("ix_artifacts_lead_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_table("lead_research_reports")
    op.execute("DROP TYPE IF EXISTS researchstatus")
    op.execute("DROP TYPE IF EXISTS confidencelevel")
    op.execute("DROP TYPE IF EXISTS artifacttype")

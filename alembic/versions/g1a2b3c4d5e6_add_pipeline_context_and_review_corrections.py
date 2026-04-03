"""add pipeline step_context_json and review_corrections table

Revision ID: g1a2b3c4d5e6
Revises: f8e9d0c1b2a3
Create Date: 2026-04-03 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "g1a2b3c4d5e6"
down_revision: str | None = "f8e9d0c1b2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add step_context_json to pipeline_runs
    op.add_column(
        "pipeline_runs",
        sa.Column("step_context_json", sa.JSON(), nullable=True),
    )

    # Create review_corrections table
    op.create_table(
        "review_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            sa.Uuid(),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("review_type", sa.String(50), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "tone", "cta", "personalization", "length",
                "accuracy", "relevance", "format", "language",
                name="correctioncategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "critical", "important", "suggestion",
                name="correctionseverity",
            ),
            nullable=False,
            server_default="suggestion",
        ),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_review_corrections_lead_id", "review_corrections", ["lead_id"])
    op.create_index("ix_review_corrections_category", "review_corrections", ["category"])
    op.create_index("ix_review_corrections_created_at", "review_corrections", ["created_at"])
    op.create_index("ix_review_corrections_review_type", "review_corrections", ["review_type"])


def downgrade() -> None:
    op.drop_index("ix_review_corrections_review_type", table_name="review_corrections")
    op.drop_index("ix_review_corrections_created_at", table_name="review_corrections")
    op.drop_index("ix_review_corrections_category", table_name="review_corrections")
    op.drop_index("ix_review_corrections_lead_id", table_name="review_corrections")
    op.drop_table("review_corrections")
    op.execute("DROP TYPE IF EXISTS correctioncategory")
    op.execute("DROP TYPE IF EXISTS correctionseverity")
    op.drop_column("pipeline_runs", "step_context_json")

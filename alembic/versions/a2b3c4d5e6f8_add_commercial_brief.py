"""add commercial brief

Revision ID: a2b3c4d5e6f8
Revises: c3d4e5f6a7b9
Create Date: 2026-04-02 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f8"
down_revision: Union[str, None] = "c3d4e5f6a7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("research_report_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "generated", "reviewed", "failed",
                name="briefstatus",
            ),
            nullable=False,
        ),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column(
            "budget_tier",
            sa.Enum(
                "low", "medium", "high", "premium",
                name="budgettier",
            ),
            nullable=True,
        ),
        sa.Column(
            "estimated_budget_min", sa.Float(), nullable=True
        ),
        sa.Column(
            "estimated_budget_max", sa.Float(), nullable=True
        ),
        sa.Column(
            "estimated_scope",
            sa.Enum(
                "landing",
                "institutional_web",
                "catalog",
                "ecommerce",
                "redesign",
                "automation",
                "branding_web",
                name="estimatedscope",
            ),
            nullable=True,
        ),
        sa.Column(
            "recommended_contact_method",
            sa.Enum(
                "whatsapp",
                "email",
                "call",
                "demo_first",
                "manual_review",
                name="contactmethod",
            ),
            nullable=True,
        ),
        sa.Column(
            "should_call",
            sa.Enum("yes", "no", "maybe", name="calldecision"),
            nullable=True,
        ),
        sa.Column("call_reason", sa.Text(), nullable=True),
        sa.Column(
            "why_this_lead_matters", sa.Text(), nullable=True
        ),
        sa.Column(
            "main_business_signals", sa.JSON(), nullable=True
        ),
        sa.Column("main_digital_gaps", sa.JSON(), nullable=True),
        sa.Column("recommended_angle", sa.Text(), nullable=True),
        sa.Column("demo_recommended", sa.Boolean(), nullable=True),
        sa.Column(
            "contact_priority",
            sa.Enum(
                "immediate", "high", "normal", "low",
                name="contactpriority",
            ),
            nullable=True,
        ),
        sa.Column(
            "generator_model", sa.String(100), nullable=True
        ),
        sa.Column(
            "reviewer_model", sa.String(100), nullable=True
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["research_report_id"],
            ["lead_research_reports.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("lead_id"),
    )

    # pricing_matrix on operational_settings already added by prior migration


def downgrade() -> None:
    op.drop_table("commercial_briefs")
    op.execute("DROP TYPE IF EXISTS briefstatus")
    op.execute("DROP TYPE IF EXISTS budgettier")
    op.execute("DROP TYPE IF EXISTS estimatedscope")
    op.execute("DROP TYPE IF EXISTS contactmethod")
    op.execute("DROP TYPE IF EXISTS calldecision")
    op.execute("DROP TYPE IF EXISTS contactpriority")

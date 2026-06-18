"""Create discussion analytics tables.

Revision ID: 20260611_0001
Revises:
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discussion_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "participant_type",
            sa.Enum(
                "student",
                "educator",
                name="participant_type",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("region_area", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=80), nullable=False),
        sa.Column("student_age_band", sa.String(length=16), nullable=False),
        sa.Column("educator_role", sa.String(length=40), nullable=True),
        sa.Column("education_setting", sa.String(length=40), nullable=True),
        sa.Column("support_goal", sa.String(length=40), nullable=True),
        sa.Column(
            "severity",
            sa.Enum(
                "ordinary-political-expression",
                "offensive-or-harmful-expression",
                "potential-hate-speech",
                "high-severity-incitement-risk",
                name="severity_tier",
                native_enum=False,
                create_constraint=True,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("incident_detected", sa.Boolean(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.Column("constructive_response", sa.Boolean(), nullable=False),
        sa.Column(
            "reviewer_outcome",
            sa.Enum(
                "bridge-response-adapted",
                "educational-activity-created",
                "safeguarding-guidance-prioritised",
                "expert-review-requested",
                name="reviewer_outcome",
                native_enum=False,
                create_constraint=True,
                length=48,
            ),
            nullable=True,
        ),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("analysis_version", sa.String(length=40), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discussion_analyses"),
        sa.UniqueConstraint(
            "session_id",
            name="uq_discussion_analyses_session_id",
        ),
    )
    op.create_index(
        "ix_discussion_analyses_dashboard_filters",
        "discussion_analyses",
        ["completed_at", "country", "language", "participant_type"],
        unique=False,
    )

    op.create_table(
        "discussion_bridge_promoters",
        sa.Column("discussion_id", sa.Uuid(), nullable=False),
        sa.Column(
            "promoter",
            sa.Enum(
                "contextualisation",
                "outgroup-empathy",
                "corroboration",
                "superordinate-identity",
                "ingroup-bias-recognition",
                name="bridge_promoter",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["discussion_id"],
            ["discussion_analyses.id"],
            name="fk_discussion_bridge_promoters_discussion_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "discussion_id",
            "promoter",
            name="pk_discussion_bridge_promoters",
        ),
    )
    op.create_table(
        "discussion_semantic_barriers",
        sa.Column("discussion_id", sa.Uuid(), nullable=False),
        sa.Column(
            "barrier",
            sa.Enum(
                "rigid-opposition",
                "stigma",
                "distrust",
                "collective-blame",
                "motive-undermining",
                name="semantic_barrier",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["discussion_id"],
            ["discussion_analyses.id"],
            name="fk_discussion_semantic_barriers_discussion_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "discussion_id",
            "barrier",
            name="pk_discussion_semantic_barriers",
        ),
    )


def downgrade() -> None:
    op.drop_table("discussion_semantic_barriers")
    op.drop_table("discussion_bridge_promoters")
    op.drop_index(
        "ix_discussion_analyses_dashboard_filters",
        table_name="discussion_analyses",
    )
    op.drop_table("discussion_analyses")

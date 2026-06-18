"""Store semantic cluster analysis events.

Revision ID: 20260614_0003
Revises: 20260612_0002
Create Date: 2026-06-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_0003"
down_revision: str | None = "20260612_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_cluster_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("classification_event_id", sa.Uuid(), nullable=False),
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
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("parent_category", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=300), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_outlier", sa.Boolean(), nullable=False),
        sa.Column("assignment_method", sa.String(length=80), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("keywords_topic_id", sa.Integer(), nullable=False),
        sa.Column("coordinate_x", sa.Float(), nullable=False),
        sa.Column("coordinate_y", sa.Float(), nullable=False),
        sa.Column("projection_version", sa.String(length=120), nullable=False),
        sa.Column("nearest_topic_id", sa.Integer(), nullable=False),
        sa.Column(
            "nearest_parent_category",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column("nearest_category", sa.String(length=300), nullable=True),
        sa.Column(
            "classification_version",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_semantic_cluster_analyses"),
        sa.UniqueConstraint(
            "classification_event_id",
            name="uq_semantic_cluster_analyses_classification_event_id",
        ),
    )
    op.create_index(
        "ix_semantic_cluster_analyses_dashboard_filters",
        "semantic_cluster_analyses",
        ["created_at", "country", "language", "participant_type"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_cluster_analyses_session_id",
        "semantic_cluster_analyses",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_cluster_analyses_session_id",
        table_name="semantic_cluster_analyses",
    )
    op.drop_index(
        "ix_semantic_cluster_analyses_dashboard_filters",
        table_name="semantic_cluster_analyses",
    )
    op.drop_table("semantic_cluster_analyses")

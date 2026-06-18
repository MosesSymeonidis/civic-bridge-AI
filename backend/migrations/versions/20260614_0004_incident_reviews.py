"""Add incident review audit fields.

Revision ID: 20260614_0004
Revises: 20260614_0003
Create Date: 2026-06-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_0004"
down_revision: str | None = "20260614_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discussion_analyses",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "discussion_analyses",
        sa.Column("reviewer_reference", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "discussion_analyses",
        sa.Column("reviewer_notes", sa.String(length=2000), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE discussion_analyses "
            "SET reviewed_at = completed_at "
            "WHERE reviewer_outcome IS NOT NULL"
        )
    )
    op.create_index(
        "ix_discussion_analyses_review_queue",
        "discussion_analyses",
        ["human_review_required", "reviewed_at", "completed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_discussion_analyses_review_queue",
        table_name="discussion_analyses",
    )
    op.drop_column("discussion_analyses", "reviewer_notes")
    op.drop_column("discussion_analyses", "reviewer_reference")
    op.drop_column("discussion_analyses", "reviewed_at")

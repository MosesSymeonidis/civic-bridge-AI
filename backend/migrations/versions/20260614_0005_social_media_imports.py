"""Add social media CSV import persistence.

Revision ID: 20260614_0005
Revises: 20260614_0004
Create Date: 2026-06-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_0005"
down_revision: str | None = "20260614_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_discussion_analyses_participant_type"),
        "discussion_analyses",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_discussion_analyses_participant_type"),
        "discussion_analyses",
        "participant_type IN ('student', 'educator', 'social-media')",
    )
    op.drop_constraint(
        op.f("ck_semantic_cluster_analyses_participant_type"),
        "semantic_cluster_analyses",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_semantic_cluster_analyses_participant_type"),
        "semantic_cluster_analyses",
        "participant_type IN ('student', 'educator', 'social-media')",
    )

    op.create_table(
        "social_media_import_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=True),
        sa.Column("source_reference", sa.String(length=200), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discussion_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("semantic_cluster_analysis_id", sa.Uuid(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["discussion_analysis_id"],
            ["discussion_analyses.id"],
            name=op.f(
                "fk_social_media_import_events_discussion_analysis_id"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_cluster_analysis_id"],
            ["semantic_cluster_analyses.id"],
            name=op.f(
                "fk_social_media_import_events_semantic_cluster_analysis_id"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_social_media_import_events"),
        ),
        sa.UniqueConstraint(
            "discussion_analysis_id",
            name=op.f(
                "uq_social_media_import_events_discussion_analysis_id"
            ),
        ),
        sa.UniqueConstraint(
            "post_id",
            name=op.f("uq_social_media_import_events_post_id"),
        ),
        sa.UniqueConstraint(
            "semantic_cluster_analysis_id",
            name=op.f(
                "uq_social_media_import_events_semantic_cluster_analysis_id"
            ),
        ),
    )


def downgrade() -> None:
    op.drop_table("social_media_import_events")
    op.execute(
        sa.text(
            "DELETE FROM semantic_cluster_analyses "
            "WHERE participant_type = 'social-media'"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM discussion_analyses "
            "WHERE participant_type = 'social-media'"
        )
    )
    op.drop_constraint(
        op.f("ck_semantic_cluster_analyses_participant_type"),
        "semantic_cluster_analyses",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_semantic_cluster_analyses_participant_type"),
        "semantic_cluster_analyses",
        "participant_type IN ('student', 'educator')",
    )
    op.drop_constraint(
        op.f("ck_discussion_analyses_participant_type"),
        "discussion_analyses",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_discussion_analyses_participant_type"),
        "discussion_analyses",
        "participant_type IN ('student', 'educator')",
    )

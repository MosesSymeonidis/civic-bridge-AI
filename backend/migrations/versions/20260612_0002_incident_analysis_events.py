"""Store incident analysis events.

Revision ID: 20260612_0002
Revises: 20260611_0001
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_0002"
down_revision: str | None = "20260611_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_discussion_analyses_session_id",
        "discussion_analyses",
        type_="unique",
    )
    op.add_column(
        "discussion_analyses",
        sa.Column("analysis_event_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "discussion_analyses",
        sa.Column("analysis_payload", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_discussion_analyses_session_id",
        "discussion_analyses",
        ["session_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_discussion_analyses_analysis_event_id",
        "discussion_analyses",
        ["analysis_event_id"],
    )

    op.drop_constraint(
        op.f("ck_discussion_semantic_barriers_semantic_barrier"),
        "discussion_semantic_barriers",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_discussion_semantic_barriers_semantic_barrier"),
        "discussion_semantic_barriers",
        (
            "barrier IN ('rigid-opposition', 'transfer-of-meaning', "
            "'prohibited-thoughts', 'stigma', 'distrust', 'bracketing', "
            "'collective-blame', 'motive-undermining')"
        ),
    )

    op.drop_constraint(
        op.f("ck_discussion_bridge_promoters_bridge_promoter"),
        "discussion_bridge_promoters",
        type_="check",
    )
    op.alter_column(
        "discussion_bridge_promoters",
        "promoter",
        existing_type=sa.String(length=40),
        type_=sa.String(length=56),
        existing_nullable=False,
    )
    op.create_check_constraint(
        op.f("ck_discussion_bridge_promoters_bridge_promoter"),
        "discussion_bridge_promoters",
        (
            "promoter IN ('contextualisation', 'outgroup-empathy', "
            "'corroboration', 'superordinate-identity', "
            "'ingroup-bias-recognition', "
            "'condemnation-of-harm-regardless-of-perpetrator')"
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM discussion_analyses "
            "WHERE analysis_event_id IS NOT NULL"
        )
    )
    op.drop_constraint(
        "uq_discussion_analyses_analysis_event_id",
        "discussion_analyses",
        type_="unique",
    )
    op.drop_index(
        "ix_discussion_analyses_session_id",
        table_name="discussion_analyses",
    )
    op.drop_column("discussion_analyses", "analysis_payload")
    op.drop_column("discussion_analyses", "analysis_event_id")
    op.create_unique_constraint(
        "uq_discussion_analyses_session_id",
        "discussion_analyses",
        ["session_id"],
    )

    op.drop_constraint(
        op.f("ck_discussion_semantic_barriers_semantic_barrier"),
        "discussion_semantic_barriers",
        type_="check",
    )
    op.execute(
        sa.text(
            "DELETE FROM discussion_semantic_barriers "
            "WHERE barrier IN ('transfer-of-meaning', "
            "'prohibited-thoughts', 'bracketing')"
        )
    )
    op.create_check_constraint(
        op.f("ck_discussion_semantic_barriers_semantic_barrier"),
        "discussion_semantic_barriers",
        (
            "barrier IN ('rigid-opposition', 'stigma', 'distrust', "
            "'collective-blame', 'motive-undermining')"
        ),
    )

    op.drop_constraint(
        op.f("ck_discussion_bridge_promoters_bridge_promoter"),
        "discussion_bridge_promoters",
        type_="check",
    )
    op.execute(
        sa.text(
            "DELETE FROM discussion_bridge_promoters "
            "WHERE promoter = "
            "'condemnation-of-harm-regardless-of-perpetrator'"
        )
    )
    op.alter_column(
        "discussion_bridge_promoters",
        "promoter",
        existing_type=sa.String(length=56),
        type_=sa.String(length=40),
        existing_nullable=False,
    )
    op.create_check_constraint(
        op.f("ck_discussion_bridge_promoters_bridge_promoter"),
        "discussion_bridge_promoters",
        (
            "promoter IN ('contextualisation', 'outgroup-empathy', "
            "'corroboration', 'superordinate-identity', "
            "'ingroup-bias-recognition')"
        ),
    )

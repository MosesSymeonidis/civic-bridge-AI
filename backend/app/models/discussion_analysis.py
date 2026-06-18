from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.analytics import (
    BridgePromoter,
    ParticipantType,
    ReviewerOutcome,
    SemanticBarrier,
    SeverityTier,
)


def enum_type(enum_class: type[Enum], name: str, length: int) -> SqlEnum:
    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [value.value for value in values],
        length=length,
    )


class DiscussionAnalysis(Base):
    __tablename__ = "discussion_analyses"
    __table_args__ = (
        Index(
            "ix_discussion_analyses_dashboard_filters",
            "completed_at",
            "country",
            "language",
            "participant_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(Uuid, index=True, nullable=False)
    analysis_event_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        unique=True,
    )
    participant_type: Mapped[ParticipantType] = mapped_column(
        enum_type(ParticipantType, "participant_type", 16),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region_area: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(80), nullable=False)
    student_age_band: Mapped[str] = mapped_column(String(16), nullable=False)
    educator_role: Mapped[str | None] = mapped_column(String(40))
    education_setting: Mapped[str | None] = mapped_column(String(40))
    support_goal: Mapped[str | None] = mapped_column(String(40))
    severity: Mapped[SeverityTier] = mapped_column(
        enum_type(SeverityTier, "severity_tier", 48),
        nullable=False,
    )
    incident_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    constructive_response: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    reviewer_outcome: Mapped[ReviewerOutcome | None] = mapped_column(
        enum_type(ReviewerOutcome, "reviewer_outcome", 48)
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    analysis_version: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="prototype-v1",
    )
    analysis_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_reference: Mapped[str | None] = mapped_column(String(120))
    reviewer_notes: Mapped[str | None] = mapped_column(String(2000))
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    semantic_barriers: Mapped[list["DiscussionSemanticBarrier"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    bridge_promoters: Mapped[list["DiscussionBridgePromoter"]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DiscussionSemanticBarrier(Base):
    __tablename__ = "discussion_semantic_barriers"

    discussion_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("discussion_analyses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    barrier: Mapped[SemanticBarrier] = mapped_column(
        enum_type(SemanticBarrier, "semantic_barrier", 32),
        primary_key=True,
    )
    discussion: Mapped[DiscussionAnalysis] = relationship(
        back_populates="semantic_barriers"
    )


class DiscussionBridgePromoter(Base):
    __tablename__ = "discussion_bridge_promoters"

    discussion_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("discussion_analyses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    promoter: Mapped[BridgePromoter] = mapped_column(
        enum_type(BridgePromoter, "bridge_promoter", 56),
        primary_key=True,
    )
    discussion: Mapped[DiscussionAnalysis] = relationship(
        back_populates="bridge_promoters"
    )

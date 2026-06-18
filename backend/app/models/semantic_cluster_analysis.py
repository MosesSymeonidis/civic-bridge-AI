from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.analytics import ParticipantType
from app.models.discussion_analysis import enum_type


class SemanticClusterAnalysis(Base):
    __tablename__ = "semantic_cluster_analyses"
    __table_args__ = (
        Index(
            "ix_semantic_cluster_analyses_dashboard_filters",
            "created_at",
            "country",
            "language",
            "participant_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    classification_event_id: Mapped[UUID] = mapped_column(
        Uuid,
        unique=True,
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(Uuid, index=True, nullable=False)
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

    topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_category: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(300))
    confidence: Mapped[float | None] = mapped_column(Float)
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assignment_method: Mapped[str] = mapped_column(String(80), nullable=False)
    keywords: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    keywords_topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    coordinate_x: Mapped[float] = mapped_column(Float, nullable=False)
    coordinate_y: Mapped[float] = mapped_column(Float, nullable=False)
    projection_version: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    nearest_topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    nearest_parent_category: Mapped[str | None] = mapped_column(String(200))
    nearest_category: Mapped[str | None] = mapped_column(String(300))
    classification_version: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="semantic-cluster-api-v1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

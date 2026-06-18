from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SocialMediaImportEvent(Base):
    __tablename__ = "social_media_import_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
    )
    platform: Mapped[str | None] = mapped_column(String(80))
    source_reference: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    discussion_analysis_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("discussion_analyses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    semantic_cluster_analysis_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("semantic_cluster_analyses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

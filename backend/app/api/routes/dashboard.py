from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.domain.analytics import ParticipantType
from app.schemas.analytics import (
    DashboardSummaryResponse,
    DashboardTimeRange,
    IncidentReviewCreate,
    IncidentReviewItem,
    IncidentReviewQueueResponse,
)
from app.services.discussion_analytics import (
    IncidentReviewNotRequiredError,
    build_dashboard_summary,
    list_incident_reviews,
    review_incident,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    time_range: Annotated[DashboardTimeRange, Query()] = (
        DashboardTimeRange.days_30
    ),
    country: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    language: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    participant_type: Annotated[ParticipantType | None, Query()] = None,
    minimum_group_size: Annotated[int, Query(ge=1, le=100)] = (
        settings.dashboard_minimum_group_size
    ),
) -> DashboardSummaryResponse:
    response.headers["Cache-Control"] = "no-store"
    return build_dashboard_summary(
        db,
        time_range=time_range,
        country=country,
        language=language,
        participant_type=participant_type,
        minimum_group_size=minimum_group_size,
    )


@router.get("/reviews", response_model=IncidentReviewQueueResponse)
async def get_incident_reviews(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    time_range: Annotated[DashboardTimeRange, Query()] = (
        DashboardTimeRange.days_30
    ),
    country: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    language: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    participant_type: Annotated[ParticipantType | None, Query()] = None,
    reviewed: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> IncidentReviewQueueResponse:
    response.headers["Cache-Control"] = "no-store"
    return list_incident_reviews(
        db,
        time_range=time_range,
        country=country,
        language=language,
        participant_type=participant_type,
        reviewed=reviewed,
        limit=limit,
    )


@router.patch(
    "/reviews/{discussion_id}",
    response_model=IncidentReviewItem,
)
async def update_incident_review(
    discussion_id: UUID,
    request: IncidentReviewCreate,
    db: Annotated[Session, Depends(get_db)],
) -> IncidentReviewItem:
    try:
        review = review_incident(db, discussion_id, request)
    except IncidentReviewNotRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This incident does not require human review.",
        ) from error
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident review item not found.",
        )
    return review

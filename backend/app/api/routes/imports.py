from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import (
    SocialMediaImportCheckRequest,
    SocialMediaImportCheckResponse,
    SocialMediaImportCreate,
    SocialMediaImportResponse,
)
from app.services.social_media_imports import (
    existing_social_media_post_ids,
    import_social_media_event,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post(
    "/social-media/check",
    response_model=SocialMediaImportCheckResponse,
)
async def check_social_media_posts(
    request: SocialMediaImportCheckRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SocialMediaImportCheckResponse:
    response.headers["Cache-Control"] = "no-store"
    return SocialMediaImportCheckResponse(
        existing_post_ids=existing_social_media_post_ids(
            db,
            request.post_ids,
        )
    )


@router.post(
    "/social-media/events",
    response_model=SocialMediaImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_social_media_import(
    request: SocialMediaImportCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SocialMediaImportResponse:
    return import_social_media_event(db, request)

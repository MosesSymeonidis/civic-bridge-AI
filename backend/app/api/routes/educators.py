from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import (
    DiscussionCompletionCreate,
    DiscussionCompletionResponse,
    IncidentAnalysisCreate,
    SemanticClusterAnalysisCreate,
    SemanticClusterAnalysisResponse,
)
from app.schemas.educator import (
    EducatorContext,
    EducatorMessageCreate,
    EducatorMessageResponse,
    EducatorSessionCreate,
    EducatorSessionResponse,
)
from app.services.discussion_analytics import (
    DiscussionAlreadyCompletedError,
    complete_educator_discussion,
    record_educator_incident_analysis,
)
from app.services.educator_chat import educator_chat_service
from app.services.semantic_cluster_analytics import (
    record_educator_semantic_cluster,
)

router = APIRouter(prefix="/educators", tags=["educators"])


@router.post(
    "/sessions",
    response_model=EducatorSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_educator_session(
    request: EducatorSessionCreate,
) -> EducatorSessionResponse:
    context = EducatorContext.model_validate(request.model_dump())
    session = educator_chat_service.create_session(context)

    return EducatorSessionResponse(
        session_id=session.session_id,
        context=session.context,
        welcome_message=educator_chat_service.welcome_message(session.context),
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=EducatorMessageResponse,
)
async def create_educator_message(
    session_id: UUID,
    request: EducatorMessageCreate,
) -> EducatorMessageResponse:
    session = educator_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Educator session not found.",
        )

    assistant_message = educator_chat_service.reply(
        session,
        request.message,
    )
    return EducatorMessageResponse(
        session_id=session.session_id,
        context=session.context,
        assistant_message=assistant_message,
    )


@router.post(
    "/sessions/{session_id}/complete",
    response_model=DiscussionCompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_educator_session(
    session_id: UUID,
    request: DiscussionCompletionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DiscussionCompletionResponse:
    session = educator_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Educator session not found.",
        )

    try:
        return complete_educator_discussion(db, session, request)
    except DiscussionAlreadyCompletedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Educator discussion has already been completed.",
        ) from error


@router.post(
    "/sessions/{session_id}/analyses",
    response_model=DiscussionCompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_educator_incident_analysis(
    session_id: UUID,
    request: IncidentAnalysisCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DiscussionCompletionResponse:
    session = educator_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Educator session not found.",
        )

    try:
        return record_educator_incident_analysis(db, session, request)
    except DiscussionAlreadyCompletedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident analysis could not be stored.",
        ) from error


@router.post(
    "/sessions/{session_id}/classifications",
    response_model=SemanticClusterAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_educator_semantic_classification(
    session_id: UUID,
    request: SemanticClusterAnalysisCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SemanticClusterAnalysisResponse:
    session = educator_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Educator session not found.",
        )

    return record_educator_semantic_cluster(db, session, request)

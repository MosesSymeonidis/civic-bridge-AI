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
from app.schemas.student import (
    StudentContext,
    StudentMessageCreate,
    StudentMessageResponse,
    StudentSessionCreate,
    StudentSessionResponse,
)
from app.services.discussion_analytics import (
    DiscussionAlreadyCompletedError,
    complete_student_discussion,
    record_student_incident_analysis,
)
from app.services.semantic_cluster_analytics import (
    record_student_semantic_cluster,
)
from app.services.student_chat import student_chat_service

router = APIRouter(prefix="/students", tags=["students"])


@router.post(
    "/sessions",
    response_model=StudentSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student_session(
    request: StudentSessionCreate,
) -> StudentSessionResponse:
    context = StudentContext.model_validate(request.model_dump())
    session = student_chat_service.create_session(context)

    return StudentSessionResponse(
        session_id=session.session_id,
        context=session.context,
        welcome_message=student_chat_service.welcome_message(session.context),
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=StudentMessageResponse,
)
async def create_student_message(
    session_id: UUID,
    request: StudentMessageCreate,
) -> StudentMessageResponse:
    session = student_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student session not found.",
        )

    assistant_message = student_chat_service.reply(
        session,
        request.message.strip(),
    )
    return StudentMessageResponse(
        session_id=session.session_id,
        context=session.context,
        assistant_message=assistant_message,
    )


@router.post(
    "/sessions/{session_id}/complete",
    response_model=DiscussionCompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_student_session(
    session_id: UUID,
    request: DiscussionCompletionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DiscussionCompletionResponse:
    session = student_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student session not found.",
        )

    try:
        return complete_student_discussion(db, session, request)
    except DiscussionAlreadyCompletedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student discussion has already been completed.",
        ) from error


@router.post(
    "/sessions/{session_id}/analyses",
    response_model=DiscussionCompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student_incident_analysis(
    session_id: UUID,
    request: IncidentAnalysisCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DiscussionCompletionResponse:
    session = student_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student session not found.",
        )

    try:
        return record_student_incident_analysis(db, session, request)
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
async def create_student_semantic_classification(
    session_id: UUID,
    request: SemanticClusterAnalysisCreate,
    db: Annotated[Session, Depends(get_db)],
) -> SemanticClusterAnalysisResponse:
    session = student_chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student session not found.",
        )

    return record_student_semantic_cluster(db, session, request)

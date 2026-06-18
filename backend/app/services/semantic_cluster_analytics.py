from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.analytics import ParticipantType
from app.models.semantic_cluster_analysis import SemanticClusterAnalysis
from app.schemas.analytics import (
    SemanticClusterAnalysisCreate,
    SemanticClusterAnalysisResponse,
)
from app.services.educator_chat import EducatorSession
from app.services.student_chat import StudentSession


def _response(
    analysis: SemanticClusterAnalysis,
) -> SemanticClusterAnalysisResponse:
    return SemanticClusterAnalysisResponse(
        id=analysis.id,
        classification_event_id=analysis.classification_event_id,
        session_id=analysis.session_id,
        participant_type=analysis.participant_type,
        topic_id=analysis.topic_id,
        parent_category=analysis.parent_category,
        category=analysis.category,
        confidence=analysis.confidence,
        is_outlier=analysis.is_outlier,
        projection_version=analysis.projection_version,
        classification_version=analysis.classification_version,
        created_at=analysis.created_at,
    )


def _persist(
    db: Session,
    *,
    session_id: UUID,
    participant_type: ParticipantType,
    country: str,
    region_area: str,
    language: str,
    student_age_band: str,
    request: SemanticClusterAnalysisCreate,
    educator_role: str | None = None,
    education_setting: str | None = None,
    support_goal: str | None = None,
) -> SemanticClusterAnalysisResponse:
    existing = db.scalar(
        select(SemanticClusterAnalysis).where(
            SemanticClusterAnalysis.classification_event_id
            == request.classification_event_id
        )
    )
    if existing is not None:
        return _response(existing)

    classification = request.classification
    analysis = SemanticClusterAnalysis(
        classification_event_id=request.classification_event_id,
        session_id=session_id,
        participant_type=participant_type,
        country=country,
        region_area=region_area,
        language=language,
        student_age_band=student_age_band,
        educator_role=educator_role,
        education_setting=education_setting,
        support_goal=support_goal,
        topic_id=classification.topic_id,
        parent_category=classification.parent_category,
        category=classification.category,
        confidence=classification.confidence,
        is_outlier=classification.is_outlier,
        assignment_method=classification.assignment_method,
        keywords=[
            keyword.model_dump(mode="json")
            for keyword in classification.keywords
        ],
        keywords_topic_id=classification.keywords_topic_id,
        coordinate_x=classification.coordinates.x,
        coordinate_y=classification.coordinates.y,
        projection_version=classification.coordinates.projection_version,
        nearest_topic_id=classification.nearest_candidate.topic_id,
        nearest_parent_category=(
            classification.nearest_candidate.parent_category
        ),
        nearest_category=classification.nearest_candidate.category,
        classification_version=request.classification_version,
    )
    db.add(analysis)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(SemanticClusterAnalysis).where(
                SemanticClusterAnalysis.classification_event_id
                == request.classification_event_id
            )
        )
        if existing is not None:
            return _response(existing)
        raise

    db.refresh(analysis)
    return _response(analysis)


def record_student_semantic_cluster(
    db: Session,
    session: StudentSession,
    request: SemanticClusterAnalysisCreate,
) -> SemanticClusterAnalysisResponse:
    return _persist(
        db,
        session_id=session.session_id,
        participant_type=ParticipantType.student,
        country=session.context.country,
        region_area=session.context.region_area,
        language=session.context.language,
        student_age_band=session.context.age_band.value,
        request=request,
    )


def record_educator_semantic_cluster(
    db: Session,
    session: EducatorSession,
    request: SemanticClusterAnalysisCreate,
) -> SemanticClusterAnalysisResponse:
    return _persist(
        db,
        session_id=session.session_id,
        participant_type=ParticipantType.educator,
        country=session.context.country,
        region_area=session.context.region_area,
        language=session.context.language,
        student_age_band=session.context.learner_age_band.value,
        educator_role=session.context.educator_role.value,
        education_setting=session.context.education_setting.value,
        support_goal=session.context.support_goal.value,
        request=request,
    )

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.analytics import (
    HUMAN_REVIEW_SEVERITIES,
    INCIDENT_SEVERITIES,
    RAG_BARRIER_MAP,
    RAG_PROMOTER_MAP,
    RAG_TIER_MAP,
    ParticipantType,
)
from app.models.discussion_analysis import (
    DiscussionAnalysis,
    DiscussionBridgePromoter,
    DiscussionSemanticBarrier,
)
from app.models.semantic_cluster_analysis import SemanticClusterAnalysis
from app.models.social_media_import import SocialMediaImportEvent
from app.schemas.analytics import (
    SocialMediaImportCreate,
    SocialMediaImportResponse,
)


def existing_social_media_post_ids(
    db: Session,
    post_ids: list[str],
) -> list[str]:
    return list(
        db.scalars(
            select(SocialMediaImportEvent.post_id)
            .where(SocialMediaImportEvent.post_id.in_(post_ids))
            .order_by(SocialMediaImportEvent.post_id)
        ).all()
    )


def _response(
    event: SocialMediaImportEvent,
    status: str,
) -> SocialMediaImportResponse:
    return SocialMediaImportResponse(
        post_id=event.post_id,
        status=status,
        discussion_analysis_id=event.discussion_analysis_id,
        semantic_cluster_analysis_id=event.semantic_cluster_analysis_id,
    )


def import_social_media_event(
    db: Session,
    request: SocialMediaImportCreate,
) -> SocialMediaImportResponse:
    existing = db.scalar(
        select(SocialMediaImportEvent).where(
            SocialMediaImportEvent.post_id == request.post_id
        )
    )
    if existing is not None:
        return _response(existing, "duplicate")

    session_id = uuid5(
        NAMESPACE_URL,
        f"civic-bridge-social-media-session:{request.post_id}",
    )
    event_id = uuid5(
        NAMESPACE_URL,
        f"civic-bridge-social-media-analysis:{request.post_id}",
    )
    barriers = list(
        dict.fromkeys(
            mapped
            for barrier in request.analysis.barriers
            if (mapped := RAG_BARRIER_MAP.get(barrier.id)) is not None
        )
    )
    promoters = list(
        dict.fromkeys(
            mapped
            for barrier in request.analysis.barriers
            for promoter in barrier.promoters
            if (mapped := RAG_PROMOTER_MAP.get(promoter)) is not None
        )
    )
    severity = RAG_TIER_MAP[request.analysis.tier]
    region_area = request.region_area or "Unspecified"

    discussion = DiscussionAnalysis(
        session_id=session_id,
        analysis_event_id=event_id,
        participant_type=ParticipantType.social_media,
        country=request.country,
        region_area=region_area,
        language=request.language,
        student_age_band="unknown",
        severity=severity,
        incident_detected=severity in INCIDENT_SEVERITIES,
        human_review_required=severity in HUMAN_REVIEW_SEVERITIES,
        constructive_response=False,
        message_count=1,
        analysis_version="social-media-csv-v1",
        analysis_payload={
            **request.analysis.model_dump(mode="json"),
            "incident_text": request.incident_text,
        },
        semantic_barriers=[
            DiscussionSemanticBarrier(barrier=barrier)
            for barrier in barriers
        ],
        bridge_promoters=[
            DiscussionBridgePromoter(promoter=promoter)
            for promoter in promoters
        ],
    )
    classification = request.classification
    semantic_cluster = SemanticClusterAnalysis(
        classification_event_id=event_id,
        session_id=session_id,
        participant_type=ParticipantType.social_media,
        country=request.country,
        region_area=region_area,
        language=request.language,
        student_age_band="unknown",
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
        classification_version="social-media-csv-v1",
    )
    try:
        db.add_all([discussion, semantic_cluster])
        db.flush()
        import_event = SocialMediaImportEvent(
            post_id=request.post_id,
            platform=request.platform,
            source_reference=request.source_reference,
            published_at=request.published_at,
            discussion_analysis_id=discussion.id,
            semantic_cluster_analysis_id=semantic_cluster.id,
        )
        db.add(import_event)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(SocialMediaImportEvent).where(
                SocialMediaImportEvent.post_id == request.post_id
            )
        )
        if existing is not None:
            return _response(existing, "duplicate")
        raise

    db.refresh(import_event)
    return _response(import_event, "imported")

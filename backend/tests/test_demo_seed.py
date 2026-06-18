from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.analytics import ParticipantType, SeverityTier
from app.models.discussion_analysis import DiscussionAnalysis
from app.models.semantic_cluster_analysis import SemanticClusterAnalysis
from app.scripts.seed_demo_data import (
    DEMO_ANALYSIS_VERSION,
    DEMO_CLASSIFICATION_VERSION,
    delete_demo_data,
    seed_demo_data,
)


def test_demo_seed_is_repeatable_and_preserves_real_records(
    database_session: Session,
) -> None:
    real_discussion = DiscussionAnalysis(
        session_id=uuid4(),
        participant_type=ParticipantType.student,
        country="Cyprus",
        region_area="Nicosia",
        language="English",
        student_age_band="14-17",
        severity=SeverityTier.ordinary_political_expression,
        incident_detected=False,
        human_review_required=False,
        constructive_response=False,
        message_count=1,
        analysis_version="production-v1",
    )
    database_session.add(real_discussion)
    real_classification = SemanticClusterAnalysis(
        classification_event_id=uuid4(),
        session_id=real_discussion.session_id,
        participant_type=ParticipantType.student,
        country="Cyprus",
        region_area="Nicosia",
        language="English",
        student_age_band="14-17",
        topic_id=2,
        parent_category="Anti-Muslim and Anti-Arab Hate",
        category="Anti-Muslim Ideology and Rights Rhetoric",
        confidence=0.7,
        is_outlier=False,
        assignment_method="embedding_cosine_similarity",
        keywords=[{"term": "rights", "weight": 0.8}],
        keywords_topic_id=2,
        coordinate_x=2.2,
        coordinate_y=6.3,
        projection_version="production-projection-v1",
        nearest_topic_id=2,
        nearest_parent_category="Anti-Muslim and Anti-Arab Hate",
        nearest_category="Anti-Muslim Ideology and Rights Rhetoric",
        classification_version="production-v1",
    )
    database_session.add(real_classification)
    database_session.commit()

    now = datetime(2026, 6, 11, 12, tzinfo=timezone.utc)
    first_count = seed_demo_data(database_session, now=now, days=5)
    second_count = seed_demo_data(database_session, now=now, days=5)

    demo_count = database_session.scalar(
        select(func.count(DiscussionAnalysis.id)).where(
            DiscussionAnalysis.analysis_version == DEMO_ANALYSIS_VERSION
        )
    )
    real_count = database_session.scalar(
        select(func.count(DiscussionAnalysis.id)).where(
            DiscussionAnalysis.analysis_version == "production-v1"
        )
    )
    demo_classification_count = database_session.scalar(
        select(func.count(SemanticClusterAnalysis.id)).where(
            SemanticClusterAnalysis.classification_version
            == DEMO_CLASSIFICATION_VERSION
        )
    )
    real_classification_count = database_session.scalar(
        select(func.count(SemanticClusterAnalysis.id)).where(
            SemanticClusterAnalysis.classification_version == "production-v1"
        )
    )

    assert first_count == 25
    assert second_count == 25
    assert demo_count == 25
    assert real_count == 1
    assert demo_classification_count == 25
    assert real_classification_count == 1

    deleted_discussions, deleted_classifications = delete_demo_data(
        database_session
    )
    database_session.commit()

    assert deleted_discussions == 25
    assert deleted_classifications == 25
    assert database_session.scalar(
        select(func.count(DiscussionAnalysis.id))
    ) == 1
    assert database_session.scalar(
        select(func.count(SemanticClusterAnalysis.id))
    ) == 1

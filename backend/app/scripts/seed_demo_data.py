from datetime import datetime, timedelta, timezone
from math import cos, radians, sin
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.domain.analytics import (
    HUMAN_REVIEW_SEVERITIES,
    INCIDENT_SEVERITIES,
    BridgePromoter,
    ParticipantType,
    ReviewerOutcome,
    SemanticBarrier,
    SeverityTier,
)
from app.models.discussion_analysis import (
    DiscussionAnalysis,
    DiscussionBridgePromoter,
    DiscussionSemanticBarrier,
)
from app.models.semantic_cluster_analysis import SemanticClusterAnalysis

DEMO_ANALYSIS_VERSION = "synthetic-demo-v1"
DEMO_CLASSIFICATION_VERSION = "synthetic-cluster-demo-v1"
DEMO_PROJECTION_VERSION = "hatexplain-umap-2d-2026-06-13"
DEMO_DAYS = 730

REGIONS = (
    "Nicosia",
    "Limassol",
    "Larnaca",
    "Paphos",
    "Famagusta area",
)
LANGUAGES = ("Greek", "Turkish", "English")
AGE_BANDS = ("6-9", "10-13", "14-17", "18+")
EDUCATOR_ROLES = (
    "classroom-teacher",
    "school-leader",
    "counselor-psychologist",
    "youth-worker",
)
EDUCATION_SETTINGS = (
    "primary-school",
    "secondary-school",
    "higher-education",
    "non-formal-youth",
)
SUPPORT_GOALS = (
    "understand-incident",
    "support-learner",
    "classroom-activity",
    "counter-narrative",
    "reporting-next-steps",
)
CLUSTER_TOPICS = (
    {
        "topic_id": 2,
        "parent_category": "Anti-Muslim and Anti-Arab Hate",
        "category": "Anti-Muslim Ideology and Rights Rhetoric",
        "center": (2.215, 6.261),
        "keywords": ("islam", "muslim", "rights"),
    },
    {
        "topic_id": 3,
        "parent_category": "Misogyny",
        "category": "Misogynistic Sexual Harassment and Rape Apologia",
        "center": (6.185, 6.410),
        "keywords": ("women", "harassment", "victim"),
    },
    {
        "topic_id": 5,
        "parent_category": "Anti-Muslim and Anti-Arab Hate",
        "category": "Anti-Arab and Anti-Muslim Ethnic Slurs",
        "center": (5.803, 2.018),
        "keywords": ("arab", "muslim", "slur"),
    },
    {
        "topic_id": 8,
        "parent_category": "Antisemitism",
        "category": "Antisemitic Generalizations",
        "center": (2.575, 3.670),
        "keywords": ("jewish", "blame", "generalization"),
    },
    {
        "topic_id": 12,
        "parent_category": "Anti-Immigrant and Refugee Hate",
        "category": "Anti-Immigrant Illegal-Status Rhetoric",
        "center": (2.906, 8.727),
        "keywords": ("immigrant", "illegal", "crime"),
    },
    {
        "topic_id": 18,
        "parent_category": "Anti-Immigrant and Refugee Hate",
        "category": "Anti-Muslim Refugee Exclusion",
        "center": (2.649, 7.754),
        "keywords": ("refugee", "exclude", "remove"),
    },
    {
        "topic_id": 22,
        "parent_category": "Anti-LGBTQ Hate",
        "category": "Anti-LGBTQ Political Rhetoric",
        "center": (6.628, 7.733),
        "keywords": ("lgbtq", "political", "rights"),
    },
    {
        "topic_id": 27,
        "parent_category": "Antisemitism",
        "category": "Antisemitic White-Genocide Conspiracies",
        "center": (3.010, 3.895),
        "keywords": ("conspiracy", "immigration", "genocide"),
    },
)

DEMO_INCIDENT_TEXTS = {
    SeverityTier.ordinary_political_expression: (
        "A participant criticised a public policy without targeting a "
        "protected group."
    ),
    SeverityTier.offensive_or_harmful_expression: (
        "A participant used insulting language during a disagreement."
    ),
    SeverityTier.potential_hate_speech: (
        "A post applied a degrading stereotype to an entire protected group."
    ),
    SeverityTier.high_severity_incitement_risk: (
        "A post encouraged others to threaten and exclude members of a "
        "protected group."
    ),
}


def _records_per_day(days_ago: int) -> int:
    if days_ago < 30:
        return 5
    if days_ago < 90:
        return 4
    if days_ago < 365:
        return 3
    return 2


def _weighted_value(values: tuple, weights: tuple[int, ...], seed: int):
    position = seed % sum(weights)
    cumulative = 0
    for value, weight in zip(values, weights, strict=True):
        cumulative += weight
        if position < cumulative:
            return value
    return values[-1]


def _semantic_barriers(seed: int) -> list[DiscussionSemanticBarrier]:
    barriers = tuple(SemanticBarrier)
    selected = {
        _weighted_value(
            barriers,
            (28, 10, 8, 20, 14, 8, 7, 5),
            seed * 7 + 3,
        )
    }
    if seed % 3 == 0:
        selected.add(
            _weighted_value(
                barriers,
                (18, 12, 10, 18, 16, 10, 9, 7),
                seed * 11 + 47,
            )
        )
    return [
        DiscussionSemanticBarrier(barrier=barrier)
        for barrier in sorted(selected, key=lambda item: item.value)
    ]


def _bridge_promoters(seed: int) -> list[DiscussionBridgePromoter]:
    promoters = tuple(BridgePromoter)
    selected = {
        _weighted_value(promoters, (27, 21, 17, 14, 11, 10), seed * 13 + 5)
    }
    if seed % 4 == 0:
        selected.add(
            _weighted_value(
                promoters,
                (20, 21, 18, 16, 14, 11),
                seed * 17 + 29,
            )
        )
    return [
        DiscussionBridgePromoter(promoter=promoter)
        for promoter in sorted(selected, key=lambda item: item.value)
    ]


def delete_demo_data(db: Session) -> tuple[int, int]:
    classification_count = int(
        db.scalar(
            select(func.count(SemanticClusterAnalysis.id)).where(
                SemanticClusterAnalysis.classification_version
                == DEMO_CLASSIFICATION_VERSION
            )
        )
        or 0
    )
    discussion_count = int(
        db.scalar(
            select(func.count(DiscussionAnalysis.id)).where(
                DiscussionAnalysis.analysis_version == DEMO_ANALYSIS_VERSION
            )
        )
        or 0
    )
    db.execute(
        delete(SemanticClusterAnalysis).where(
            SemanticClusterAnalysis.classification_version
            == DEMO_CLASSIFICATION_VERSION
        )
    )
    demo_discussions = (
        DiscussionAnalysis.analysis_version == DEMO_ANALYSIS_VERSION
    )
    db.execute(
        delete(DiscussionSemanticBarrier).where(
            DiscussionSemanticBarrier.discussion.has(demo_discussions)
        )
    )
    db.execute(
        delete(DiscussionBridgePromoter).where(
            DiscussionBridgePromoter.discussion.has(demo_discussions)
        )
    )
    db.execute(delete(DiscussionAnalysis).where(demo_discussions))
    return discussion_count, classification_count


def seed_demo_data(
    db: Session,
    *,
    now: datetime | None = None,
    days: int = DEMO_DAYS,
) -> int:
    generated_at = (now or datetime.now(timezone.utc)).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    delete_demo_data(db)

    severity_values = tuple(SeverityTier)
    outcome_values = tuple(ReviewerOutcome)
    created = 0

    for days_ago in range(days):
        for daily_index in range(_records_per_day(days_ago)):
            seed = days_ago * 17 + daily_index * 31
            participant_type = _weighted_value(
                tuple(ParticipantType),
                (64, 36),
                seed,
            )
            severity = _weighted_value(
                severity_values,
                (43, 30, 20, 7),
                seed * 7,
            )
            region = _weighted_value(
                REGIONS,
                (35, 24, 17, 14, 10),
                seed * 11,
            )
            language = _weighted_value(
                LANGUAGES,
                (47, 24, 29),
                seed * 13,
            )
            age_band = _weighted_value(
                AGE_BANDS,
                (10, 24, 45, 21),
                seed * 19,
            )
            reviewer_outcome = (
                _weighted_value(
                    outcome_values,
                    (68, 21, 8, 3),
                    seed * 23 + 7,
                )
                if seed % 5 != 0
                else None
            )
            constructive_response = (
                reviewer_outcome
                == ReviewerOutcome.bridge_response_adapted
                or seed % 3 != 0
            )
            session_id = uuid5(
                NAMESPACE_URL,
                (
                    f"civic-bridge-demo:{days_ago}:{daily_index}:"
                    f"{generated_at.date().isoformat()}"
                ),
            )

            discussion = DiscussionAnalysis(
                session_id=session_id,
                participant_type=participant_type,
                country="Cyprus",
                region_area=region,
                language=language,
                student_age_band=age_band,
                educator_role=(
                    EDUCATOR_ROLES[seed % len(EDUCATOR_ROLES)]
                    if participant_type == ParticipantType.educator
                    else None
                ),
                education_setting=(
                    EDUCATION_SETTINGS[seed % len(EDUCATION_SETTINGS)]
                    if participant_type == ParticipantType.educator
                    else None
                ),
                support_goal=(
                    SUPPORT_GOALS[seed % len(SUPPORT_GOALS)]
                    if participant_type == ParticipantType.educator
                    else None
                ),
                severity=severity,
                incident_detected=severity in INCIDENT_SEVERITIES,
                human_review_required=severity in HUMAN_REVIEW_SEVERITIES,
                constructive_response=constructive_response,
                reviewer_outcome=reviewer_outcome,
                message_count=2 + seed % 10,
                analysis_version=DEMO_ANALYSIS_VERSION,
                analysis_payload={
                    "incident_text": DEMO_INCIDENT_TEXTS[severity],
                },
                completed_at=generated_at
                - timedelta(days=days_ago, hours=daily_index * 2),
                semantic_barriers=_semantic_barriers(seed),
                bridge_promoters=_bridge_promoters(seed),
            )
            db.add(discussion)

            topic = _weighted_value(
                CLUSTER_TOPICS,
                (19, 14, 12, 10, 16, 12, 10, 7),
                seed * 29 + 11,
            )
            angle = radians(seed % 360)
            radius = 0.06 + (seed % 9) * 0.018
            coordinate_x = topic["center"][0] + cos(angle) * radius
            coordinate_y = topic["center"][1] + sin(angle) * radius
            db.add(
                SemanticClusterAnalysis(
                    classification_event_id=uuid5(
                        NAMESPACE_URL,
                        f"civic-bridge-demo-cluster:{session_id}",
                    ),
                    session_id=session_id,
                    participant_type=participant_type,
                    country="Cyprus",
                    region_area=region,
                    language=language,
                    student_age_band=age_band,
                    educator_role=discussion.educator_role,
                    education_setting=discussion.education_setting,
                    support_goal=discussion.support_goal,
                    topic_id=topic["topic_id"],
                    parent_category=topic["parent_category"],
                    category=topic["category"],
                    confidence=round(0.45 + (seed % 45) / 100, 2),
                    is_outlier=False,
                    assignment_method="embedding_cosine_similarity",
                    keywords=[
                        {
                            "term": keyword,
                            "weight": round(0.9 - index * 0.16, 2),
                        }
                        for index, keyword in enumerate(topic["keywords"])
                    ],
                    keywords_topic_id=topic["topic_id"],
                    coordinate_x=coordinate_x,
                    coordinate_y=coordinate_y,
                    projection_version=DEMO_PROJECTION_VERSION,
                    nearest_topic_id=topic["topic_id"],
                    nearest_parent_category=topic["parent_category"],
                    nearest_category=topic["category"],
                    classification_version=DEMO_CLASSIFICATION_VERSION,
                    created_at=discussion.completed_at,
                )
            )
            created += 1

    db.commit()
    return created


def main() -> None:
    if not settings.seed_demo_data:
        with SessionLocal() as db:
            discussion_count, classification_count = delete_demo_data(db)
            db.commit()
        print(
            "Demo data seeding disabled. Removed "
            f"{discussion_count} synthetic discussions and "
            f"{classification_count} synthetic classifications."
        )
        return

    with SessionLocal() as db:
        created = seed_demo_data(db)
    print(f"Seeded {created} synthetic discussion analytics records.")


if __name__ == "__main__":
    main()

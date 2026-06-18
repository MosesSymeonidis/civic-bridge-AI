import calendar
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.analytics import (
    BRIDGE_PROMOTER_LABELS,
    HUMAN_REVIEW_SEVERITIES,
    INCIDENT_SEVERITIES,
    PARTICIPANT_TYPE_LABELS,
    RAG_BARRIER_MAP,
    RAG_PROMOTER_MAP,
    RAG_TIER_MAP,
    REVIEWER_OUTCOME_LABELS,
    SEMANTIC_BARRIER_LABELS,
    SEVERITY_LABELS,
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
from app.schemas.analytics import (
    DashboardAppliedFilters,
    DashboardDistributionItem,
    DashboardPeriod,
    DashboardSemanticClusterCategory,
    DashboardSemanticClusterPlot,
    DashboardSemanticClusterPoint,
    DashboardSummaryResponse,
    DashboardTimeRange,
    DashboardTotals,
    DashboardTrendPoint,
    DiscussionCompletionCreate,
    DiscussionCompletionResponse,
    IncidentAnalysisRationale,
    IncidentAnalysisCreate,
    IncidentReviewBarrier,
    IncidentReviewCreate,
    IncidentReviewItem,
    IncidentReviewQueueResponse,
)
from app.services.educator_chat import EducatorSession
from app.services.student_chat import StudentSession


class DiscussionAlreadyCompletedError(Exception):
    pass


class IncidentReviewNotRequiredError(Exception):
    pass


SEMANTIC_CLUSTER_POINT_LIMIT = 2000


def _message_count(messages: list[tuple[str, str]], role: str) -> int:
    return sum(1 for message_role, _ in messages if message_role == role)


def _incident_text_from_messages(
    messages: list[tuple[str, str]],
    role: str,
) -> str:
    return "\n\n".join(
        content for message_role, content in messages if message_role == role
    )


def _incident_text_from_payload(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""

    incident_text = str(payload.get("incident_text", "")).strip()
    if incident_text:
        return incident_text

    spans = [
        str(item.get("span", "")).strip()
        for item in payload.get("barriers", [])
        if isinstance(item, dict) and item.get("span")
    ]
    return "\n".join(dict.fromkeys(spans))


def _completion_response(
    discussion: DiscussionAnalysis,
) -> DiscussionCompletionResponse:
    return DiscussionCompletionResponse(
        id=discussion.id,
        session_id=discussion.session_id,
        analysis_event_id=discussion.analysis_event_id,
        participant_type=discussion.participant_type,
        country=discussion.country,
        region_area=discussion.region_area,
        language=discussion.language,
        student_age_band=discussion.student_age_band,
        severity=discussion.severity,
        semantic_barriers=[
            item.barrier for item in discussion.semantic_barriers
        ],
        bridge_promoters=[
            item.promoter for item in discussion.bridge_promoters
        ],
        incident_detected=discussion.incident_detected,
        human_review_required=discussion.human_review_required,
        constructive_response=discussion.constructive_response,
        reviewer_outcome=discussion.reviewer_outcome,
        message_count=discussion.message_count,
        analysis_version=discussion.analysis_version,
        completed_at=discussion.completed_at,
    )


def _review_item(discussion: DiscussionAnalysis) -> IncidentReviewItem:
    payload = discussion.analysis_payload or {}
    incident_text = _incident_text_from_payload(payload)
    rationale = [
        IncidentAnalysisRationale.model_validate(item)
        for item in payload.get("rationale", [])
        if isinstance(item, dict)
    ]
    barriers = [
        IncidentReviewBarrier(
            id=str(item.get("id", "")),
            rationale=str(item.get("rationale", "")),
            promoters=[
                str(promoter) for promoter in item.get("promoters", [])
            ],
        )
        for item in payload.get("barriers", [])
        if isinstance(item, dict) and item.get("id")
    ]
    return IncidentReviewItem(
        id=discussion.id,
        participant_type=discussion.participant_type,
        country=discussion.country,
        region_area=discussion.region_area,
        language=discussion.language,
        student_age_band=discussion.student_age_band,
        severity=discussion.severity,
        semantic_barriers=[
            item.barrier for item in discussion.semantic_barriers
        ],
        bridge_promoters=[
            item.promoter for item in discussion.bridge_promoters
        ],
        message_count=discussion.message_count,
        completed_at=discussion.completed_at,
        tier_label=str(payload.get("tier_label", "")),
        target_group=str(payload.get("target_group", "")),
        themes=[str(theme) for theme in payload.get("themes", [])],
        confidence=str(payload.get("confidence", "")),
        incident_text=incident_text,
        rationale=rationale,
        barriers=barriers,
        reviewed_at=discussion.reviewed_at,
        reviewer_reference=discussion.reviewer_reference,
        reviewer_notes=discussion.reviewer_notes,
        reviewer_outcome=discussion.reviewer_outcome,
        constructive_response=discussion.constructive_response,
    )


def list_incident_reviews(
    db: Session,
    *,
    time_range: DashboardTimeRange,
    country: str | None,
    language: str | None,
    participant_type: ParticipantType | None,
    reviewed: bool,
    limit: int,
) -> IncidentReviewQueueResponse:
    now = datetime.now(timezone.utc)
    start, end, _ = _period_for_range(time_range, now)
    conditions = [
        *_base_conditions(
            start,
            end,
            country,
            language,
            participant_type,
        ),
        DiscussionAnalysis.human_review_required.is_(True),
        (
            DiscussionAnalysis.reviewed_at.is_not(None)
            if reviewed
            else DiscussionAnalysis.reviewed_at.is_(None)
        ),
    ]
    total = _count(db, conditions)
    discussions = db.scalars(
        select(DiscussionAnalysis)
        .where(*conditions)
        .order_by(DiscussionAnalysis.completed_at.desc())
        .limit(limit)
    ).unique().all()
    return IncidentReviewQueueResponse(
        total=total,
        items=[_review_item(discussion) for discussion in discussions],
    )


def review_incident(
    db: Session,
    discussion_id: UUID,
    request: IncidentReviewCreate,
) -> IncidentReviewItem | None:
    discussion = db.get(DiscussionAnalysis, discussion_id)
    if discussion is None:
        return None
    if not discussion.human_review_required:
        raise IncidentReviewNotRequiredError

    discussion.reviewer_reference = request.reviewer_reference
    discussion.reviewer_notes = request.notes or None
    discussion.reviewer_outcome = request.outcome
    discussion.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(discussion)
    return _review_item(discussion)


def _persist_discussion(
    db: Session,
    *,
    session_id: UUID,
    analysis_event_id: UUID | None,
    participant_type: ParticipantType,
    country: str,
    region_area: str,
    language: str,
    student_age_band: str,
    message_count: int,
    severity: SeverityTier,
    semantic_barriers: list[SemanticBarrier],
    bridge_promoters: list[BridgePromoter],
    constructive_response: bool,
    reviewer_outcome: ReviewerOutcome | None,
    analysis_version: str,
    analysis_payload: dict[str, Any] | None = None,
    educator_role: str | None = None,
    education_setting: str | None = None,
    support_goal: str | None = None,
) -> DiscussionCompletionResponse:
    if analysis_event_id is not None:
        existing_event = db.scalar(
            select(DiscussionAnalysis).where(
                DiscussionAnalysis.analysis_event_id == analysis_event_id
            )
        )
        if existing_event is not None:
            return _completion_response(existing_event)
    else:
        existing_id = db.scalar(
            select(DiscussionAnalysis.id).where(
                DiscussionAnalysis.session_id == session_id,
                DiscussionAnalysis.analysis_event_id.is_(None),
            )
        )
        if existing_id is not None:
            raise DiscussionAlreadyCompletedError

    discussion = DiscussionAnalysis(
        session_id=session_id,
        analysis_event_id=analysis_event_id,
        participant_type=participant_type,
        country=country,
        region_area=region_area,
        language=language,
        student_age_band=student_age_band,
        educator_role=educator_role,
        education_setting=education_setting,
        support_goal=support_goal,
        severity=severity,
        incident_detected=severity in INCIDENT_SEVERITIES,
        human_review_required=severity in HUMAN_REVIEW_SEVERITIES,
        constructive_response=(
            constructive_response
            or reviewer_outcome == ReviewerOutcome.bridge_response_adapted
        ),
        reviewer_outcome=reviewer_outcome,
        message_count=message_count,
        analysis_version=analysis_version,
        analysis_payload=analysis_payload,
        reviewed_at=(
            datetime.now(timezone.utc)
            if reviewer_outcome is not None
            else None
        ),
        semantic_barriers=[
            DiscussionSemanticBarrier(barrier=barrier)
            for barrier in semantic_barriers
        ],
        bridge_promoters=[
            DiscussionBridgePromoter(promoter=promoter)
            for promoter in bridge_promoters
        ],
    )
    db.add(discussion)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if analysis_event_id is not None:
            existing_event = db.scalar(
                select(DiscussionAnalysis).where(
                    DiscussionAnalysis.analysis_event_id
                    == analysis_event_id
                )
            )
            if existing_event is not None:
                return _completion_response(existing_event)
        raise DiscussionAlreadyCompletedError from error

    db.refresh(discussion)
    return _completion_response(discussion)


def complete_student_discussion(
    db: Session,
    session: StudentSession,
    request: DiscussionCompletionCreate,
) -> DiscussionCompletionResponse:
    return _persist_discussion(
        db,
        session_id=session.session_id,
        analysis_event_id=None,
        participant_type=ParticipantType.student,
        country=session.context.country,
        region_area=session.context.region_area,
        language=session.context.language,
        student_age_band=session.context.age_band.value,
        message_count=_message_count(session.messages, "student"),
        severity=request.severity,
        semantic_barriers=request.semantic_barriers,
        bridge_promoters=request.bridge_promoters,
        constructive_response=request.constructive_response,
        reviewer_outcome=request.reviewer_outcome,
        analysis_version=request.analysis_version,
        analysis_payload={
            "incident_text": _incident_text_from_messages(
                session.messages,
                "student",
            )
        },
    )


def complete_educator_discussion(
    db: Session,
    session: EducatorSession,
    request: DiscussionCompletionCreate,
) -> DiscussionCompletionResponse:
    return _persist_discussion(
        db,
        session_id=session.session_id,
        analysis_event_id=None,
        participant_type=ParticipantType.educator,
        country=session.context.country,
        region_area=session.context.region_area,
        language=session.context.language,
        student_age_band=session.context.learner_age_band.value,
        educator_role=session.context.educator_role.value,
        education_setting=session.context.education_setting.value,
        support_goal=session.context.support_goal.value,
        message_count=_message_count(session.messages, "educator"),
        severity=request.severity,
        semantic_barriers=request.semantic_barriers,
        bridge_promoters=request.bridge_promoters,
        constructive_response=request.constructive_response,
        reviewer_outcome=request.reviewer_outcome,
        analysis_version=request.analysis_version,
        analysis_payload={
            "incident_text": _incident_text_from_messages(
                session.messages,
                "educator",
            )
        },
    )


def _labels_from_incident(
    request: IncidentAnalysisCreate,
) -> tuple[list[SemanticBarrier], list[BridgePromoter]]:
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
    return barriers, promoters


def _incident_analysis_payload(
    request: IncidentAnalysisCreate,
) -> dict[str, Any]:
    payload = request.analysis.model_dump(mode="json")
    if request.incident_text:
        payload["incident_text"] = request.incident_text
    return payload


def record_student_incident_analysis(
    db: Session,
    session: StudentSession,
    request: IncidentAnalysisCreate,
) -> DiscussionCompletionResponse:
    barriers, promoters = _labels_from_incident(request)
    return _persist_discussion(
        db,
        session_id=session.session_id,
        analysis_event_id=request.analysis_event_id,
        participant_type=ParticipantType.student,
        country=session.context.country,
        region_area=session.context.region_area,
        language=session.context.language,
        student_age_band=session.context.age_band.value,
        message_count=request.message_count,
        severity=RAG_TIER_MAP[request.analysis.tier],
        semantic_barriers=barriers,
        bridge_promoters=promoters,
        constructive_response=False,
        reviewer_outcome=None,
        analysis_version=request.analysis_version,
        analysis_payload=_incident_analysis_payload(request),
    )


def record_educator_incident_analysis(
    db: Session,
    session: EducatorSession,
    request: IncidentAnalysisCreate,
) -> DiscussionCompletionResponse:
    barriers, promoters = _labels_from_incident(request)
    return _persist_discussion(
        db,
        session_id=session.session_id,
        analysis_event_id=request.analysis_event_id,
        participant_type=ParticipantType.educator,
        country=session.context.country,
        region_area=session.context.region_area,
        language=session.context.language,
        student_age_band=session.context.learner_age_band.value,
        educator_role=session.context.educator_role.value,
        education_setting=session.context.education_setting.value,
        support_goal=session.context.support_goal.value,
        message_count=request.message_count,
        severity=RAG_TIER_MAP[request.analysis.tier],
        semantic_barriers=barriers,
        bridge_promoters=promoters,
        constructive_response=False,
        reviewer_outcome=None,
        analysis_version=request.analysis_version,
        analysis_payload=_incident_analysis_payload(request),
    )


def _subtract_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _period_for_range(
    time_range: DashboardTimeRange,
    now: datetime,
) -> tuple[datetime, datetime, str]:
    if time_range == DashboardTimeRange.days_30:
        return now - timedelta(days=30), now, "week"
    if time_range == DashboardTimeRange.days_90:
        return now - timedelta(days=90), now, "week"

    start = _subtract_months(now.replace(day=1, hour=0, minute=0, second=0), 11)
    return start, now, "month"


def _base_conditions(
    start: datetime,
    end: datetime,
    country: str | None,
    language: str | None,
    participant_type: ParticipantType | None,
) -> list[Any]:
    conditions: list[Any] = [
        DiscussionAnalysis.completed_at >= start,
        DiscussionAnalysis.completed_at < end,
    ]
    if country is not None:
        conditions.append(DiscussionAnalysis.country == country)
    if language is not None:
        conditions.append(DiscussionAnalysis.language == language)
    if participant_type is not None:
        conditions.append(
            DiscussionAnalysis.participant_type == participant_type
        )
    return conditions


def _count(db: Session, conditions: Sequence[Any]) -> int:
    return int(
        db.scalar(
            select(func.count(DiscussionAnalysis.id)).where(*conditions)
        )
        or 0
    )


def _group_counts(
    db: Session,
    column: Any,
    conditions: Sequence[Any],
    *,
    statement: Select | None = None,
) -> dict[Any, int]:
    query = statement if statement is not None else select(column, func.count())
    rows = db.execute(
        query.where(*conditions).group_by(column)
    ).all()
    return {key: int(count) for key, count in rows}


def _percentage(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count * 100 / total, 1)


def _fixed_distribution(
    counts: dict[Any, int],
    labels: dict[Enum, str],
    denominator: int,
    minimum_group_size: int,
) -> list[DashboardDistributionItem]:
    return [
        DashboardDistributionItem(
            key=item.value,
            label=label,
            count=count,
            percentage=_percentage(count, denominator),
        )
        for item, label in labels.items()
        if (count := counts.get(item, 0)) >= minimum_group_size
    ]


def _dynamic_distribution(
    counts: dict[str, int],
    denominator: int,
    minimum_group_size: int,
) -> list[DashboardDistributionItem]:
    return [
        DashboardDistributionItem(
            key=key,
            label=key,
            count=count,
            percentage=_percentage(count, denominator),
        )
        for key, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
        if count >= minimum_group_size
    ]


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _trend_points(
    rows: Sequence[tuple[ParticipantType, datetime]],
    start: datetime,
    end: datetime,
    bucket: str,
) -> list[DashboardTrendPoint]:
    if bucket == "week":
        bucket_count = ceil((end - start) / timedelta(days=7))
        starts = [start + timedelta(days=index * 7) for index in range(bucket_count)]

        def bucket_start(value: datetime) -> datetime:
            index = int((value - start) // timedelta(days=7))
            return starts[min(max(index, 0), len(starts) - 1)]

    else:
        starts = []
        current = _month_start(start)
        while current <= end:
            starts.append(current)
            current = _subtract_months(current, -1)

        def bucket_start(value: datetime) -> datetime:
            return _month_start(value)

    counts = {
        item.date(): {participant: 0 for participant in ParticipantType}
        for item in starts
    }
    for participant_type, completed_at in rows:
        normalized_at = completed_at
        if normalized_at.tzinfo is None:
            normalized_at = normalized_at.replace(tzinfo=timezone.utc)
        key = bucket_start(normalized_at).date()
        if key in counts:
            counts[key][participant_type] += 1

    return [
        DashboardTrendPoint(
            period_start=period_start,
            student=values[ParticipantType.student],
            educator=values[ParticipantType.educator],
            social_media=values[ParticipantType.social_media],
            total=sum(values.values()),
        )
        for period_start, values in counts.items()
    ]


def _semantic_cluster_plot(
    db: Session,
    *,
    start: datetime,
    end: datetime,
    country: str | None,
    language: str | None,
    participant_type: ParticipantType | None,
    minimum_group_size: int,
) -> DashboardSemanticClusterPlot:
    conditions: list[Any] = [
        SemanticClusterAnalysis.created_at >= start,
        SemanticClusterAnalysis.created_at < end,
    ]
    if country is not None:
        conditions.append(SemanticClusterAnalysis.country == country)
    if language is not None:
        conditions.append(SemanticClusterAnalysis.language == language)
    if participant_type is not None:
        conditions.append(
            SemanticClusterAnalysis.participant_type == participant_type
        )

    version_rows = db.execute(
        select(
            SemanticClusterAnalysis.projection_version,
            func.count(),
        )
        .where(*conditions)
        .group_by(SemanticClusterAnalysis.projection_version)
    ).all()
    if not version_rows:
        return DashboardSemanticClusterPlot(
            projection_version=None,
            total_points=0,
            displayed_points=0,
            categories=[],
            points=[],
        )

    projection_version = max(
        version_rows,
        key=lambda item: (int(item[1]), str(item[0])),
    )[0]
    version_conditions = [
        *conditions,
        SemanticClusterAnalysis.projection_version == projection_version,
    ]
    total_points = int(
        db.scalar(
            select(func.count(SemanticClusterAnalysis.id)).where(
                *version_conditions
            )
        )
        or 0
    )
    topic_counts = {
        int(topic_id): int(count)
        for topic_id, count in db.execute(
            select(
                SemanticClusterAnalysis.keywords_topic_id,
                func.count(),
            )
            .where(*version_conditions)
            .group_by(SemanticClusterAnalysis.keywords_topic_id)
        ).all()
        if int(count) >= minimum_group_size
    }
    if not topic_counts:
        return DashboardSemanticClusterPlot(
            projection_version=projection_version,
            total_points=total_points,
            displayed_points=0,
            categories=[],
            points=[],
        )

    analysis_rows = db.execute(
        select(
            SemanticClusterAnalysis,
            DiscussionAnalysis.analysis_payload,
        )
        .outerjoin(
            DiscussionAnalysis,
            DiscussionAnalysis.analysis_event_id
            == SemanticClusterAnalysis.classification_event_id,
        )
        .where(
            *version_conditions,
            SemanticClusterAnalysis.keywords_topic_id.in_(topic_counts),
        )
        .order_by(SemanticClusterAnalysis.created_at.desc())
        .limit(SEMANTIC_CLUSTER_POINT_LIMIT)
    ).all()
    categories: dict[int, DashboardSemanticClusterCategory] = {}
    points: list[DashboardSemanticClusterPoint] = []

    for analysis, analysis_payload in analysis_rows:
        display_category = (
            analysis.nearest_category
            if analysis.is_outlier
            else analysis.category
        )
        display_parent = (
            analysis.nearest_parent_category
            if analysis.is_outlier
            else analysis.parent_category
        )
        keywords = [
            str(keyword["term"])
            for keyword in analysis.keywords
            if isinstance(keyword, dict) and keyword.get("term")
        ]
        categories.setdefault(
            analysis.keywords_topic_id,
            DashboardSemanticClusterCategory(
                topic_id=analysis.keywords_topic_id,
                parent_category=display_parent,
                category=display_category,
                count=topic_counts[analysis.keywords_topic_id],
                keywords=keywords[:5],
            ),
        )
        points.append(
            DashboardSemanticClusterPoint(
                x=analysis.coordinate_x,
                y=analysis.coordinate_y,
                topic_id=analysis.keywords_topic_id,
                parent_category=display_parent,
                category=display_category,
                confidence=analysis.confidence,
                is_outlier=analysis.is_outlier,
                keywords=keywords[:5],
                participant_type=analysis.participant_type,
                incident_text=(
                    _incident_text_from_payload(analysis_payload)
                    or None
                ),
            )
        )

    return DashboardSemanticClusterPlot(
        projection_version=projection_version,
        total_points=total_points,
        displayed_points=len(points),
        categories=sorted(
            categories.values(),
            key=lambda item: (-item.count, item.topic_id),
        ),
        points=points,
    )


def build_dashboard_summary(
    db: Session,
    *,
    time_range: DashboardTimeRange,
    country: str | None,
    language: str | None,
    participant_type: ParticipantType | None,
    minimum_group_size: int,
) -> DashboardSummaryResponse:
    now = datetime.now(timezone.utc)
    start, end, bucket = _period_for_range(time_range, now)
    conditions = _base_conditions(
        start,
        end,
        country,
        language,
        participant_type,
    )

    total = _count(db, conditions)
    incident_conditions = [
        *conditions,
        DiscussionAnalysis.incident_detected.is_(True),
    ]
    incident_count = _count(db, incident_conditions)
    human_review_count = _count(
        db,
        [*conditions, DiscussionAnalysis.human_review_required.is_(True)],
    )
    completed_review_count = _count(
        db,
        [
            *conditions,
            DiscussionAnalysis.human_review_required.is_(True),
            DiscussionAnalysis.reviewed_at.is_not(None),
        ],
    )
    pending_review_count = human_review_count - completed_review_count
    constructive_count = _count(
        db,
        [*conditions, DiscussionAnalysis.constructive_response.is_(True)],
    )

    period_duration = end - start
    previous_conditions = _base_conditions(
        start - period_duration,
        start,
        country,
        language,
        participant_type,
    )
    previous_total = _count(db, previous_conditions)
    previous_period_change = (
        round((total - previous_total) * 100 / previous_total, 1)
        if previous_total
        else None
    )

    region_counts = _group_counts(
        db,
        DiscussionAnalysis.region_area,
        incident_conditions,
    )
    source_counts = _group_counts(
        db,
        DiscussionAnalysis.participant_type,
        conditions,
    )
    severity_counts = _group_counts(
        db,
        DiscussionAnalysis.severity,
        conditions,
    )
    age_counts = _group_counts(
        db,
        DiscussionAnalysis.student_age_band,
        conditions,
    )
    language_counts = _group_counts(
        db,
        DiscussionAnalysis.language,
        conditions,
    )
    outcome_conditions = [
        *conditions,
        DiscussionAnalysis.reviewer_outcome.is_not(None),
    ]
    outcome_counts = _group_counts(
        db,
        DiscussionAnalysis.reviewer_outcome,
        outcome_conditions,
    )
    outcome_total = sum(outcome_counts.values())

    barrier_counts = _group_counts(
        db,
        DiscussionSemanticBarrier.barrier,
        conditions,
        statement=select(
            DiscussionSemanticBarrier.barrier,
            func.count(),
        ).join(DiscussionAnalysis),
    )
    barrier_total = sum(barrier_counts.values())
    promoter_counts = _group_counts(
        db,
        DiscussionBridgePromoter.promoter,
        conditions,
        statement=select(
            DiscussionBridgePromoter.promoter,
            func.count(),
        ).join(DiscussionAnalysis),
    )
    promoter_total = sum(promoter_counts.values())

    trend_rows = db.execute(
        select(
            DiscussionAnalysis.participant_type,
            DiscussionAnalysis.completed_at,
        ).where(*incident_conditions)
    ).all()

    return DashboardSummaryResponse(
        generated_at=now,
        period=DashboardPeriod(start=start, end=end, bucket=bucket),
        filters=DashboardAppliedFilters(
            time_range=time_range,
            country=country,
            language=language,
            participant_type=participant_type,
            minimum_group_size=minimum_group_size,
        ),
        totals=DashboardTotals(
            analysed_conversations=total,
            incident_signals=incident_count,
            human_review_rate=_percentage(human_review_count, total),
            pending_reviews=pending_review_count,
            completed_reviews=completed_review_count,
            review_completion_rate=_percentage(
                completed_review_count,
                human_review_count,
            ),
            constructive_response_rate=_percentage(constructive_count, total),
            previous_period_change=previous_period_change,
        ),
        regions=_dynamic_distribution(
            region_counts,
            incident_count,
            minimum_group_size,
        ),
        trend=_trend_points(trend_rows, start, end, bucket),
        sources=_fixed_distribution(
            source_counts,
            PARTICIPANT_TYPE_LABELS,
            total,
            minimum_group_size,
        ),
        severity=_fixed_distribution(
            severity_counts,
            SEVERITY_LABELS,
            total,
            minimum_group_size,
        ),
        semantic_barriers=_fixed_distribution(
            barrier_counts,
            SEMANTIC_BARRIER_LABELS,
            barrier_total,
            minimum_group_size,
        ),
        bridge_promoters=_fixed_distribution(
            promoter_counts,
            BRIDGE_PROMOTER_LABELS,
            promoter_total,
            minimum_group_size,
        ),
        age_bands=_dynamic_distribution(
            age_counts,
            total,
            minimum_group_size,
        ),
        languages=_dynamic_distribution(
            language_counts,
            total,
            minimum_group_size,
        ),
        reviewer_outcomes=_fixed_distribution(
            outcome_counts,
            REVIEWER_OUTCOME_LABELS,
            outcome_total,
            minimum_group_size,
        ),
        semantic_clusters=_semantic_cluster_plot(
            db,
            start=start,
            end=end,
            country=country,
            language=language,
            participant_type=participant_type,
            minimum_group_size=minimum_group_size,
        ),
    )

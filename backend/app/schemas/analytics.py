from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    field_validator,
)

from app.domain.analytics import (
    BridgePromoter,
    ParticipantType,
    ReviewerOutcome,
    SemanticBarrier,
    SeverityTier,
)


class AnalyticsApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class DiscussionCompletionCreate(AnalyticsApiModel):
    severity: SeverityTier
    semantic_barriers: list[SemanticBarrier] = Field(
        default_factory=list,
        max_length=len(SemanticBarrier),
    )
    bridge_promoters: list[BridgePromoter] = Field(
        default_factory=list,
        max_length=len(BridgePromoter),
    )
    constructive_response: bool = False
    reviewer_outcome: ReviewerOutcome | None = None
    analysis_version: str = Field(
        default="prototype-v1",
        min_length=1,
        max_length=40,
    )

    @field_validator("semantic_barriers", "bridge_promoters")
    @classmethod
    def reject_duplicate_labels(cls, values: list[Enum]) -> list[Enum]:
        if len(values) != len(set(values)):
            raise ValueError("Analytical labels must be unique.")
        return values


class IncidentAnalysisRationale(AnalyticsApiModel):
    citation_id: str = Field(max_length=120)
    reason: str = Field(max_length=2000)


class IncidentAnalysisBarrier(AnalyticsApiModel):
    id: str = Field(min_length=1, max_length=80)
    span: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=2000)
    promoters: list[str] = Field(default_factory=list, max_length=20)


class IncidentAnalysisRelatedCase(AnalyticsApiModel):
    name: str | None = Field(default=None, max_length=300)
    appno: str | None = Field(default=None, max_length=120)
    conclusion: str | None = Field(default=None, max_length=1000)
    url: str | None = Field(default=None, max_length=2000)


class IncidentAnalysisSnapshot(AnalyticsApiModel):
    tier: Literal[1, 2, 3, 4]
    tier_label: str = Field(min_length=1, max_length=200)
    rationale: list[IncidentAnalysisRationale] = Field(
        default_factory=list,
        max_length=30,
    )
    barriers: list[IncidentAnalysisBarrier] = Field(
        default_factory=list,
        max_length=30,
    )
    target_group: str = Field(default="", max_length=500)
    themes: list[str] = Field(default_factory=list, max_length=30)
    confidence: str = Field(default="", max_length=80)
    related_cases: list[IncidentAnalysisRelatedCase] = Field(
        default_factory=list,
        max_length=30,
    )


class IncidentAnalysisCreate(AnalyticsApiModel):
    analysis_event_id: UUID
    message_count: int = Field(default=1, ge=1)
    incident_text: str = Field(default="", max_length=4000)
    analysis_version: str = Field(
        default="rag-incident-v1",
        min_length=1,
        max_length=40,
    )
    analysis: IncidentAnalysisSnapshot


class SemanticClusterKeyword(AnalyticsApiModel):
    term: str = Field(min_length=1, max_length=120)
    weight: FiniteFloat


class SemanticClusterCoordinates(AnalyticsApiModel):
    x: FiniteFloat
    y: FiniteFloat
    projection_version: str = Field(min_length=1, max_length=120)


class SemanticClusterCandidate(AnalyticsApiModel):
    topic_id: int
    parent_category: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=300)


class SemanticClusterSnapshot(AnalyticsApiModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic_id: int
    parent_category: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=300)
    confidence: FiniteFloat | None = Field(default=None, ge=0, le=1)
    is_outlier: bool
    assignment_method: str = Field(min_length=1, max_length=80)
    keywords_role: str = Field(min_length=1, max_length=120)
    keywords: list[SemanticClusterKeyword] = Field(
        default_factory=list,
        max_length=20,
    )
    keywords_topic_id: int
    coordinates: SemanticClusterCoordinates
    nearest_candidate: SemanticClusterCandidate


class SemanticClusterAnalysisCreate(AnalyticsApiModel):
    classification_event_id: UUID
    classification_version: str = Field(
        default="semantic-cluster-api-v1",
        min_length=1,
        max_length=40,
    )
    classification: SemanticClusterSnapshot


class SocialMediaImportCheckRequest(AnalyticsApiModel):
    post_ids: list[str] = Field(min_length=1, max_length=500)

    @field_validator("post_ids")
    @classmethod
    def validate_post_ids(cls, values: list[str]) -> list[str]:
        if any(not value or len(value) > 200 for value in values):
            raise ValueError("Post IDs must contain 1 to 200 characters.")
        return list(dict.fromkeys(values))


class SocialMediaImportCheckResponse(BaseModel):
    existing_post_ids: list[str]


class SocialMediaImportCreate(AnalyticsApiModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=2, max_length=100)
    region_area: str = Field(default="Unspecified", max_length=120)
    language: str = Field(min_length=2, max_length=80)
    platform: str | None = Field(default=None, max_length=80)
    published_at: datetime | None = None
    source_reference: str | None = Field(default=None, max_length=200)
    incident_text: str = Field(default="", max_length=4000)
    analysis: IncidentAnalysisSnapshot
    classification: SemanticClusterSnapshot


class SocialMediaImportResponse(BaseModel):
    post_id: str
    status: Literal["imported", "duplicate"]
    discussion_analysis_id: UUID
    semantic_cluster_analysis_id: UUID


class SemanticClusterAnalysisResponse(BaseModel):
    id: UUID
    classification_event_id: UUID
    session_id: UUID
    participant_type: ParticipantType
    topic_id: int
    parent_category: str | None
    category: str | None
    confidence: float | None
    is_outlier: bool
    projection_version: str
    classification_version: str
    created_at: datetime


class DiscussionCompletionResponse(BaseModel):
    id: UUID
    session_id: UUID
    analysis_event_id: UUID | None
    participant_type: ParticipantType
    country: str
    region_area: str
    language: str
    student_age_band: str
    severity: SeverityTier
    semantic_barriers: list[SemanticBarrier]
    bridge_promoters: list[BridgePromoter]
    incident_detected: bool
    human_review_required: bool
    constructive_response: bool
    reviewer_outcome: ReviewerOutcome | None
    message_count: int
    analysis_version: str
    completed_at: datetime


class IncidentReviewCreate(AnalyticsApiModel):
    reviewer_reference: str = Field(min_length=2, max_length=120)
    outcome: ReviewerOutcome | None = None
    notes: str = Field(default="", max_length=2000)


class IncidentReviewBarrier(BaseModel):
    id: str
    rationale: str
    promoters: list[str]


class IncidentReviewItem(BaseModel):
    id: UUID
    participant_type: ParticipantType
    country: str
    region_area: str
    language: str
    student_age_band: str
    severity: SeverityTier
    semantic_barriers: list[SemanticBarrier]
    bridge_promoters: list[BridgePromoter]
    message_count: int
    completed_at: datetime
    tier_label: str
    target_group: str
    themes: list[str]
    confidence: str
    incident_text: str
    rationale: list[IncidentAnalysisRationale]
    barriers: list[IncidentReviewBarrier]
    reviewed_at: datetime | None
    reviewer_reference: str | None
    reviewer_notes: str | None
    reviewer_outcome: ReviewerOutcome | None
    constructive_response: bool


class IncidentReviewQueueResponse(BaseModel):
    total: int
    items: list[IncidentReviewItem]


class DashboardTimeRange(str, Enum):
    days_30 = "30d"
    days_90 = "90d"
    months_12 = "12m"


class DashboardPeriod(BaseModel):
    start: datetime
    end: datetime
    bucket: str


class DashboardTotals(BaseModel):
    analysed_conversations: int
    incident_signals: int
    human_review_rate: float
    pending_reviews: int
    completed_reviews: int
    review_completion_rate: float
    constructive_response_rate: float
    previous_period_change: float | None


class DashboardDistributionItem(BaseModel):
    key: str
    label: str
    count: int
    percentage: float


class DashboardTrendPoint(BaseModel):
    period_start: date
    student: int
    educator: int
    social_media: int
    total: int


class DashboardAppliedFilters(BaseModel):
    time_range: DashboardTimeRange
    country: str | None
    language: str | None
    participant_type: ParticipantType | None
    minimum_group_size: int


class DashboardSemanticClusterPoint(BaseModel):
    x: float
    y: float
    topic_id: int
    parent_category: str | None
    category: str | None
    confidence: float | None
    is_outlier: bool
    keywords: list[str]
    participant_type: ParticipantType


class DashboardSemanticClusterCategory(BaseModel):
    topic_id: int
    parent_category: str | None
    category: str | None
    count: int
    keywords: list[str]


class DashboardSemanticClusterPlot(BaseModel):
    projection_version: str | None
    total_points: int
    displayed_points: int
    categories: list[DashboardSemanticClusterCategory]
    points: list[DashboardSemanticClusterPoint]


class DashboardSummaryResponse(BaseModel):
    generated_at: datetime
    period: DashboardPeriod
    filters: DashboardAppliedFilters
    totals: DashboardTotals
    regions: list[DashboardDistributionItem]
    trend: list[DashboardTrendPoint]
    sources: list[DashboardDistributionItem]
    severity: list[DashboardDistributionItem]
    semantic_barriers: list[DashboardDistributionItem]
    bridge_promoters: list[DashboardDistributionItem]
    age_bands: list[DashboardDistributionItem]
    languages: list[DashboardDistributionItem]
    reviewer_outcomes: list[DashboardDistributionItem]
    semantic_clusters: DashboardSemanticClusterPlot

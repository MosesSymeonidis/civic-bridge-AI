from enum import Enum


class ParticipantType(str, Enum):
    student = "student"
    educator = "educator"
    social_media = "social-media"


class SeverityTier(str, Enum):
    ordinary_political_expression = "ordinary-political-expression"
    offensive_or_harmful_expression = "offensive-or-harmful-expression"
    potential_hate_speech = "potential-hate-speech"
    high_severity_incitement_risk = "high-severity-incitement-risk"


class SemanticBarrier(str, Enum):
    rigid_opposition = "rigid-opposition"
    transfer_of_meaning = "transfer-of-meaning"
    prohibited_thoughts = "prohibited-thoughts"
    stigma = "stigma"
    distrust = "distrust"
    bracketing = "bracketing"
    collective_blame = "collective-blame"
    motive_undermining = "motive-undermining"


class BridgePromoter(str, Enum):
    contextualisation = "contextualisation"
    outgroup_empathy = "outgroup-empathy"
    corroboration = "corroboration"
    superordinate_identity = "superordinate-identity"
    ingroup_bias_recognition = "ingroup-bias-recognition"
    condemnation_of_harm = "condemnation-of-harm-regardless-of-perpetrator"


class ReviewerOutcome(str, Enum):
    bridge_response_adapted = "bridge-response-adapted"
    educational_activity_created = "educational-activity-created"
    safeguarding_guidance_prioritised = "safeguarding-guidance-prioritised"
    expert_review_requested = "expert-review-requested"


SEVERITY_LABELS = {
    SeverityTier.ordinary_political_expression: "Ordinary political expression",
    SeverityTier.offensive_or_harmful_expression: (
        "Offensive or harmful expression"
    ),
    SeverityTier.potential_hate_speech: "Potential hate speech - review",
    SeverityTier.high_severity_incitement_risk: (
        "High-severity incitement risk"
    ),
}

SEMANTIC_BARRIER_LABELS = {
    SemanticBarrier.rigid_opposition: "Rigid opposition",
    SemanticBarrier.transfer_of_meaning: "Transfer of meaning",
    SemanticBarrier.prohibited_thoughts: "Prohibited thoughts",
    SemanticBarrier.stigma: "Stigma",
    SemanticBarrier.distrust: "Distrust",
    SemanticBarrier.bracketing: "Bracketing",
    SemanticBarrier.collective_blame: "Collective blame",
    SemanticBarrier.motive_undermining: "Motive undermining",
}

BRIDGE_PROMOTER_LABELS = {
    BridgePromoter.contextualisation: "Contextualisation",
    BridgePromoter.outgroup_empathy: "Outgroup empathy",
    BridgePromoter.corroboration: "Corroboration",
    BridgePromoter.superordinate_identity: "Superordinate identity",
    BridgePromoter.ingroup_bias_recognition: "Ingroup bias recognition",
    BridgePromoter.condemnation_of_harm: (
        "Condemnation of harm regardless of perpetrator"
    ),
}

RAG_BARRIER_MAP = {
    "rigid_opposition": SemanticBarrier.rigid_opposition,
    "transfer_of_meaning": SemanticBarrier.transfer_of_meaning,
    "prohibited_thoughts": SemanticBarrier.prohibited_thoughts,
    "stigma": SemanticBarrier.stigma,
    "undermining_motive": SemanticBarrier.motive_undermining,
    "distrust": SemanticBarrier.distrust,
    "bracketing": SemanticBarrier.bracketing,
}

RAG_PROMOTER_MAP = {
    "recognising_ingroup_bias": BridgePromoter.ingroup_bias_recognition,
    "contextualisation": BridgePromoter.contextualisation,
    "corroboration": BridgePromoter.corroboration,
    "outgroup_empathy": BridgePromoter.outgroup_empathy,
    "superordinate_identity": BridgePromoter.superordinate_identity,
    "condemnation_of_harm_regardless_of_perpetrator": (
        BridgePromoter.condemnation_of_harm
    ),
}

RAG_TIER_MAP = {
    1: SeverityTier.ordinary_political_expression,
    2: SeverityTier.offensive_or_harmful_expression,
    3: SeverityTier.potential_hate_speech,
    4: SeverityTier.high_severity_incitement_risk,
}

REVIEWER_OUTCOME_LABELS = {
    ReviewerOutcome.bridge_response_adapted: "Bridge response adapted",
    ReviewerOutcome.educational_activity_created: "Educational activity created",
    ReviewerOutcome.safeguarding_guidance_prioritised: (
        "Safeguarding guidance prioritised"
    ),
    ReviewerOutcome.expert_review_requested: "Further expert review requested",
}

PARTICIPANT_TYPE_LABELS = {
    ParticipantType.student: "Student conversations",
    ParticipantType.educator: "Educator reports",
    ParticipantType.social_media: "Social media posts",
}

HUMAN_REVIEW_SEVERITIES = {
    SeverityTier.potential_hate_speech,
    SeverityTier.high_severity_incitement_risk,
}

INCIDENT_SEVERITIES = {
    SeverityTier.offensive_or_harmful_expression,
    SeverityTier.potential_hate_speech,
    SeverityTier.high_severity_incitement_risk,
}

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from .inference import TopicClusterer
from .projection import TopicProjector


@dataclass(frozen=True)
class ServiceSettings:
    model_path: Path
    embedding_model_path: Path
    projection_path: Path
    topic_metadata_path: Path
    min_confidence: float = 0.25


class SemanticClusteringService:
    """Single-process inference service with stable 2D coordinates."""

    def __init__(self, settings: ServiceSettings) -> None:
        self.settings = settings
        self.clusterer = TopicClusterer(
            settings.model_path,
            min_confidence=settings.min_confidence,
            embedding_model=str(settings.embedding_model_path),
            topic_metadata_path=settings.topic_metadata_path,
        )
        self.projector = TopicProjector(settings.projection_path)
        self._lock = Lock()

    @property
    def projection_version(self) -> str:
        return str(self.projector.metadata["projection_version"])

    def predict(self, text: str) -> dict:
        # The encoder and projection estimator are reused across requests.
        # Serialize access because their thread-safety guarantees vary.
        with self._lock:
            embeddings = self.clusterer.embed_many([text])
            prediction = self.clusterer.predict_many(
                [text],
                embeddings=embeddings,
            )[0]
            point = self.projector.transform(embeddings)[0]

        keywords_topic = (
            prediction.candidate_topic
            if prediction.is_outlier
            else prediction.topic
        )
        return {
            "text": text.strip(),
            "topic_id": prediction.topic,
            "parent_category": prediction.group,
            "category": prediction.label,
            "confidence": prediction.confidence,
            "is_outlier": prediction.is_outlier,
            "assignment_method": "embedding_cosine_similarity",
            "keywords_role": "topic_description_not_decision_features",
            "keywords": self.clusterer.topic_keywords(keywords_topic),
            "keywords_topic_id": keywords_topic,
            "coordinates": {
                "x": point.x,
                "y": point.y,
                "projection_version": self.projection_version,
            },
            "nearest_candidate": {
                "topic_id": prediction.candidate_topic,
                "parent_category": prediction.candidate_group,
                "category": prediction.candidate_label,
            },
        }

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class ClusterPrediction:
    """A JSON-serializable text-to-topic prediction."""

    topic: int
    candidate_topic: int
    confidence: float | None
    is_outlier: bool
    label: str | None
    candidate_label: str | None
    group: str | None
    candidate_group: str | None
    generated_label: str | None
    top_words: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TopicClusterer:
    """Load a fitted BERTopic model once and assign text to its topics."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        min_confidence: float | None = 0.25,
        embedding_model: str | None = None,
        topic_metadata_path: str | Path | None = None,
    ) -> None:
        if min_confidence is not None and not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1 or None")

        try:
            from bertopic import BERTopic
        except ImportError as exc:
            raise RuntimeError(
                "BERTopic is not installed. Install this package with its "
                "declared dependencies."
            ) from exc

        self.model_path = Path(model_path)
        self.min_confidence = min_confidence
        self.model = BERTopic.load(
            str(self.model_path),
            embedding_model=embedding_model,
        )
        self._topic_labels, self._generated_labels = self._load_topic_labels()
        self._topic_groups = self._load_topic_groups(topic_metadata_path)

    def _load_topic_labels(self) -> tuple[dict[int, str], dict[int, str]]:
        topic_info = self.model.get_topic_info()
        labels: dict[int, str] = {}
        generated: dict[int, str] = {}
        for row in topic_info.itertuples():
            topic = int(row.Topic)
            generated[topic] = str(row.Name)
            custom_name = getattr(row, "CustomName", None)
            labels[topic] = (
                str(custom_name)
                if custom_name is not None and str(custom_name) != "nan"
                else generated[topic]
            )
        return labels, generated

    def _load_topic_groups(
        self, topic_metadata_path: str | Path | None
    ) -> dict[int, str]:
        metadata_path = (
            Path(topic_metadata_path)
            if topic_metadata_path is not None
            else self.model_path.parent / "topic_labels.json"
        )
        if not metadata_path.exists():
            return {}

        from .label_model import load_topic_metadata

        metadata = load_topic_metadata(metadata_path)
        return {
            topic: values["group_label"]
            for topic, values in metadata.items()
            if values.get("group_label")
        }

    @staticmethod
    def _confidence_values(probabilities: Any, count: int) -> list[float | None]:
        if probabilities is None:
            return [None] * count

        import numpy as np

        values = np.asarray(probabilities)
        if values.ndim == 0:
            return [float(values)]
        if values.ndim == 1:
            return [float(value) for value in values]
        return [float(row.max()) for row in values]

    def predict(self, text: str) -> ClusterPrediction:
        """Assign one non-empty text to a topic."""
        return self.predict_many([text])[0]

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        """Embed a batch with the same model used by BERTopic."""
        normalized = self._normalize_texts(texts)
        return np.asarray(
            self.model._extract_embeddings(
                normalized,
                method="document",
                verbose=False,
            )
        )

    @staticmethod
    def _normalize_texts(texts: Sequence[str]) -> list[str]:
        normalized = [text.strip() for text in texts]
        if not normalized:
            return []
        if any(not text for text in normalized):
            raise ValueError("Input texts must not be empty")
        return normalized

    def predict_many(
        self,
        texts: Sequence[str],
        *,
        embeddings: np.ndarray | None = None,
    ) -> list[ClusterPrediction]:
        """Assign a batch of texts while embedding them efficiently together."""
        normalized = self._normalize_texts(texts)
        if not normalized:
            return []
        if embeddings is not None and len(embeddings) != len(normalized):
            raise ValueError("Embeddings and texts must have the same length")

        if embeddings is None:
            topics, probabilities = self.model.transform(normalized)
        else:
            topics, probabilities = self.model.transform(
                normalized,
                embeddings=embeddings,
            )
        confidences = self._confidence_values(probabilities, len(normalized))

        predictions = []
        for candidate_topic_value, confidence in zip(topics, confidences):
            candidate_topic = int(candidate_topic_value)
            rejected = candidate_topic == -1 or (
                self.min_confidence is not None
                and (confidence is None or confidence < self.min_confidence)
            )
            topic = -1 if rejected else candidate_topic
            assigned_label = self._topic_labels.get(topic)
            words = [
                word
                for word, _ in (self.model.get_topic(candidate_topic) or [])
            ]
            predictions.append(
                ClusterPrediction(
                    topic=topic,
                    candidate_topic=candidate_topic,
                    confidence=confidence,
                    is_outlier=rejected,
                    label=assigned_label,
                    candidate_label=self._topic_labels.get(candidate_topic),
                    group=self._topic_groups.get(topic),
                    candidate_group=self._topic_groups.get(candidate_topic),
                    generated_label=self._generated_labels.get(candidate_topic),
                    top_words=words,
                )
            )
        return predictions

    def topic_keywords(
        self, topic: int, *, limit: int = 10
    ) -> list[dict[str, str | float]]:
        """Return weighted c-TF-IDF/representation terms for one topic."""
        return [
            {"term": term, "weight": float(weight)}
            for term, weight in (self.model.get_topic(topic) or [])[:limit]
        ]

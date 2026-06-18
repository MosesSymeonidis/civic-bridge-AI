"""Example integration from a separate Python application."""

from hate_speech_clustering.inference import TopicClusterer


# Create this once when the application starts, not once per request.
clusterer = TopicClusterer(
    "artifacts/bertopic/model",
    min_confidence=0.25,
)


def assign_cluster(text: str) -> dict:
    """Function that can be called by an API route, worker, or service."""
    return clusterer.predict(text).to_dict()


if __name__ == "__main__":
    result = assign_cluster(
        "People from that community should not be allowed to live here."
    )
    print(result)


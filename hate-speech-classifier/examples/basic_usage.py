"""Minimal BERTopic example using the prepared HateXplain dataset."""

from __future__ import annotations

import argparse
import random
from collections import Counter

from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from hate_speech_clustering.dataset import read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/processed/hatexplain.jsonl",
        help="Prepared HateXplain JSONL file.",
    )
    parser.add_argument("--documents", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Keep the test split untouched and discover themes only within content
    # already annotated as hate speech or offensive.
    records = [
        record
        for record in read_jsonl(args.input)
        if record["split"] == "train"
        and record["content_label"] in {"hatespeech", "offensive"}
    ]
    records = random.Random(args.seed).sample(
        records, min(args.documents, len(records))
    )
    documents = [record["text"] for record in records]

    embedding_model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric="cosine",
            random_state=args.seed,
        ),
        hdbscan_model=HDBSCAN(
            min_cluster_size=15,
            min_samples=5,
            metric="euclidean",
            prediction_data=True,
        ),
        vectorizer_model=CountVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
        ),
        representation_model=KeyBERTInspired(),
        verbose=True,
    )

    topics, _ = topic_model.fit_transform(documents)

    print("\nDiscovered topics")
    print(topic_model.get_topic_info()[["Topic", "Count", "Name"]].to_string(index=False))

    # Labels are not used to create these clusters. They are joined afterward
    # to explain the composition of each discovered topic.
    print("\nComposition of each topic")
    for topic in sorted(set(topics)):
        topic_records = [
            record
            for record, assigned_topic in zip(records, topics)
            if assigned_topic == topic
        ]
        content_counts = Counter(
            record["content_label"] for record in topic_records
        )
        target_counts = Counter(
            target
            for record in topic_records
            for target in record["target_labels"]
        )
        print(
            f"topic={topic:>2} documents={len(topic_records):>3} "
            f"content={dict(content_counts)} "
            f"top_targets={target_counts.most_common(3)}"
        )

    # Assign a new post after fitting. Topic -1 means the post is an outlier.
    new_posts = [
        "People from that community should not be allowed to live here."
    ]
    predicted_topics, probabilities = topic_model.transform(new_posts)
    print("\nNew-post assignment")
    print(
        {
            "topic": int(predicted_topics[0]),
            "probability": float(probabilities[0]),
        }
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Sequence

from .dataset import read_jsonl
from .reporting import content_label_rows, target_label_rows, write_csv

DEFAULT_LABELS = ["hatespeech", "offensive"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover semantic topics in normalized HateXplain posts."
    )
    parser.add_argument(
        "--input", default="data/processed/hatexplain.jsonl", help="Input JSONL."
    )
    parser.add_argument(
        "--output-dir", default="artifacts/bertopic", help="Artifact directory."
    )
    parser.add_argument(
        "--split",
        choices=["train", "val", "test", "all"],
        default="train",
        help="Official split used to fit the topic model.",
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        default=DEFAULT_LABELS,
        help="Content labels to include, or the single value 'all'.",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence-transformers model name or local path.",
    )
    parser.add_argument("--min-topic-size", type=int, default=30)
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--guided-content-labels",
        action="store_true",
        help="Use the single content label to guide UMAP before clustering.",
    )
    parser.add_argument(
        "--skip-keybert",
        action="store_true",
        help="Use only c-TF-IDF topic terms.",
    )
    return parser


def select_records(
    records: Sequence[dict[str, Any]],
    *,
    split: str,
    labels: Sequence[str],
    max_documents: int | None,
    seed: int,
) -> list[dict[str, Any]]:
    include_all_labels = list(labels) == ["all"]
    selected = [
        record
        for record in records
        if (split == "all" or record["split"] == split)
        and (include_all_labels or record["content_label"] in labels)
    ]
    if max_documents is not None and len(selected) > max_documents:
        indices = sorted(random.Random(seed).sample(range(len(selected)), max_documents))
        selected = [selected[index] for index in indices]
    return selected


def _probability_at(probabilities: Any, index: int) -> float | None:
    if probabilities is None:
        return None
    value = probabilities[index]
    if hasattr(value, "ndim") and value.ndim:
        return float(value.max())
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        from bertopic import BERTopic
        from bertopic.representation import KeyBERTInspired
        from hdbscan import HDBSCAN
        from sentence_transformers import SentenceTransformer
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.preprocessing import LabelEncoder
        from umap import UMAP
    except ImportError as exc:
        raise SystemExit(
            "BERTopic dependencies are missing. Run `pip install -e .` first."
        ) from exc

    records = select_records(
        list(read_jsonl(args.input)),
        split=args.split,
        labels=args.labels,
        max_documents=args.max_documents,
        seed=args.seed,
    )
    if len(records) < args.min_topic_size:
        raise SystemExit(
            f"Only {len(records)} documents matched; lower --min-topic-size or "
            "change the filters."
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    documents = [record["text"] for record in records]
    embedding_model = SentenceTransformer(args.embedding_model)
    umap_model = UMAP(
        n_neighbors=args.n_neighbors,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=args.seed,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=args.min_topic_size,
        min_samples=args.min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    vectorizer_model = CountVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )
    representation_model = None if args.skip_keybert else KeyBERTInspired()
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        representation_model=representation_model,
        calculate_probabilities=False,
        verbose=True,
    )

    y = None
    if args.guided_content_labels:
        y = LabelEncoder().fit_transform(
            [record["content_label"] for record in records]
        )
    topics, probabilities = topic_model.fit_transform(documents, y=y)
    integer_topics = [int(topic) for topic in topics]

    topic_model.get_topic_info().to_csv(output_dir / "topic_info.csv", index=False)
    topics_per_class = topic_model.topics_per_class(
        documents, classes=[record["content_label"] for record in records]
    )
    topics_per_class.to_csv(output_dir / "topics_per_class.csv", index=False)

    document_rows = []
    for index, (record, topic) in enumerate(zip(records, integer_topics)):
        document_rows.append(
            {
                "post_id": record["post_id"],
                "split": record["split"],
                "content_label": record["content_label"],
                "target_labels": "|".join(record["target_labels"]),
                "topic": topic,
                "probability": _probability_at(probabilities, index),
                "text": record["text"],
            }
        )
    write_csv(
        document_rows,
        output_dir / "document_topics.csv",
        [
            "post_id",
            "split",
            "content_label",
            "target_labels",
            "topic",
            "probability",
            "text",
        ],
    )
    write_csv(
        content_label_rows(records, integer_topics),
        output_dir / "topic_content_labels.csv",
        ["topic", "content_label", "count", "topic_share"],
    )
    write_csv(
        target_label_rows(records, integer_topics),
        output_dir / "topic_targets.csv",
        ["topic", "target_label", "document_count", "topic_document_share"],
    )

    topic_terms = {
        str(topic): [
            {"term": term, "weight": float(weight)}
            for term, weight in (topic_model.get_topic(topic) or [])
        ]
        for topic in sorted(set(integer_topics))
    }
    (output_dir / "topic_terms.json").write_text(
        json.dumps(topic_terms, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    non_outlier_topics = {topic for topic in integer_topics if topic != -1}
    report = {
        "documents": len(records),
        "embedding_model": args.embedding_model,
        "split": args.split,
        "labels": args.labels,
        "guided_content_labels": args.guided_content_labels,
        "min_topic_size": args.min_topic_size,
        "min_samples": args.min_samples,
        "n_neighbors": args.n_neighbors,
        "seed": args.seed,
        "topic_count_excluding_outliers": len(non_outlier_topics),
        "outlier_documents": integer_topics.count(-1),
        "outlier_rate": integer_topics.count(-1) / len(integer_topics),
    }
    (output_dir / "run_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    topic_model.save(
        output_dir / "model",
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=args.embedding_model,
    )
    print(
        f"Wrote {len(records)} assignments and "
        f"{len(non_outlier_topics)} non-outlier topics to {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


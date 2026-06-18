from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


def load_topic_metadata(path: str | Path) -> dict[int, dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    topics = payload.get("topics", payload)
    metadata = {
        int(topic): dict(values)
        for topic, values in topics.items()
    }

    assigned_topics: set[int] = set()
    for group_id, group in payload.get("groups", {}).items():
        for topic_value in group["topics"]:
            topic = int(topic_value)
            if topic in assigned_topics:
                raise ValueError(f"Topic {topic} belongs to multiple groups")
            if topic not in metadata:
                raise ValueError(f"Group {group_id} references unknown topic {topic}")
            assigned_topics.add(topic)
            metadata[topic]["group_id"] = group_id
            metadata[topic]["group_label"] = group["label"]

    if payload.get("groups"):
        missing = sorted(set(metadata) - assigned_topics)
        if missing:
            raise ValueError(f"Topics missing a parent group: {missing}")
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply reviewed custom labels to a saved BERTopic model."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
    )
    parser.add_argument(
        "--topic-info-output",
        help="Optional path for the labeled topic information CSV.",
    )
    parser.add_argument(
        "--document-topics",
        help="Optional existing document topic-assignment CSV to enrich.",
    )
    parser.add_argument(
        "--document-output",
        help="Output path for enriched document assignments.",
    )
    parser.add_argument(
        "--group-summary-output",
        help="Optional grouped document-count report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    from bertopic import BERTopic

    metadata = load_topic_metadata(args.labels)
    model = BERTopic.load(args.model)
    model_topics = set(int(topic) for topic in model.get_topic_info()["Topic"])
    metadata_topics = set(metadata)
    if model_topics != metadata_topics:
        missing = sorted(model_topics - metadata_topics)
        unexpected = sorted(metadata_topics - model_topics)
        raise SystemExit(
            f"Topic mismatch. Missing labels: {missing}; "
            f"unexpected labels: {unexpected}"
        )

    model.set_topic_labels(
        {topic: values["label"] for topic, values in metadata.items()}
    )
    model.save(
        args.model,
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=args.embedding_model,
    )

    if args.topic_info_output:
        topic_info = model.get_topic_info()
        topic_info["Category"] = topic_info["Topic"].map(
            {topic: values["category"] for topic, values in metadata.items()}
        )
        topic_info["GroupId"] = topic_info["Topic"].map(
            {topic: values.get("group_id") for topic, values in metadata.items()}
        )
        topic_info["Group"] = topic_info["Topic"].map(
            {topic: values.get("group_label") for topic, values in metadata.items()}
        )
        topic_info["Description"] = topic_info["Topic"].map(
            {topic: values["description"] for topic, values in metadata.items()}
        )
        output_path = Path(args.topic_info_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        topic_info.to_csv(output_path, index=False)

    if bool(args.document_topics) != bool(args.document_output):
        raise SystemExit(
            "--document-topics and --document-output must be provided together"
        )
    if args.document_topics:
        import pandas as pd

        documents = pd.read_csv(args.document_topics)
        documents.insert(
            documents.columns.get_loc("topic") + 1,
            "topic_label",
            documents["topic"].map(
                {topic: values["label"] for topic, values in metadata.items()}
            ),
        )
        documents.insert(
            documents.columns.get_loc("topic_label") + 1,
            "topic_category",
            documents["topic"].map(
                {topic: values["category"] for topic, values in metadata.items()}
            ),
        )
        documents.insert(
            documents.columns.get_loc("topic_category") + 1,
            "topic_group_id",
            documents["topic"].map(
                {topic: values.get("group_id") for topic, values in metadata.items()}
            ),
        )
        documents.insert(
            documents.columns.get_loc("topic_group_id") + 1,
            "topic_group",
            documents["topic"].map(
                {
                    topic: values.get("group_label")
                    for topic, values in metadata.items()
                }
            ),
        )
        document_output = Path(args.document_output)
        document_output.parent.mkdir(parents=True, exist_ok=True)
        documents.to_csv(document_output, index=False)

        if args.group_summary_output:
            group_summary = (
                documents.groupby(["topic_group_id", "topic_group"], dropna=False)
                .agg(
                    document_count=("post_id", "size"),
                    topic_count=("topic", "nunique"),
                    hate_speech_count=(
                        "content_label",
                        lambda values: int((values == "hatespeech").sum()),
                    ),
                    offensive_count=(
                        "content_label",
                        lambda values: int((values == "offensive").sum()),
                    ),
                )
                .reset_index()
                .sort_values("document_count", ascending=False)
            )
            summary_output = Path(args.group_summary_output)
            summary_output.parent.mkdir(parents=True, exist_ok=True)
            group_summary.to_csv(summary_output, index=False)
    elif args.group_summary_output:
        raise SystemExit(
            "--group-summary-output requires --document-topics and "
            "--document-output"
        )

    print(f"Applied {len(metadata)} reviewed labels to {args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

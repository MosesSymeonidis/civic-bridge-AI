from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence


def content_label_rows(
    records: Sequence[dict[str, Any]], topics: Sequence[int]
) -> list[dict[str, Any]]:
    totals = Counter(topics)
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    for record, topic in zip(records, topics):
        counts[int(topic)][record["content_label"]] += 1

    return [
        {
            "topic": topic,
            "content_label": label,
            "count": count,
            "topic_share": count / totals[topic],
        }
        for topic in sorted(counts)
        for label, count in sorted(counts[topic].items())
    ]


def target_label_rows(
    records: Sequence[dict[str, Any]], topics: Sequence[int]
) -> list[dict[str, Any]]:
    totals = Counter(topics)
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    for record, topic_value in zip(records, topics):
        topic = int(topic_value)
        targets = record["target_labels"] or ["__no_consensus_target__"]
        counts[topic].update(set(targets))

    return [
        {
            "topic": topic,
            "target_label": target,
            "document_count": count,
            "topic_document_share": count / totals[topic],
        }
        for topic in sorted(counts)
        for target, count in sorted(counts[topic].items())
    ]


def write_csv(
    rows: Iterable[dict[str, Any]], path: str | Path, fieldnames: Sequence[str]
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

UNDECIDED = "undecided"
NO_TARGET = "None"


def consensus_label(labels: Iterable[str]) -> tuple[str, dict[str, int]]:
    """Return a majority label, or ``undecided`` when no majority exists."""
    votes = Counter(label.lower() for label in labels)
    if not votes:
        return UNDECIDED, {}

    label, count = votes.most_common(1)[0]
    winners = [name for name, value in votes.items() if value == count]
    if count < 2 or len(winners) != 1:
        return UNDECIDED, dict(sorted(votes.items()))
    return label, dict(sorted(votes.items()))


def target_votes(annotations: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Count at most one vote per target and annotator."""
    votes: Counter[str] = Counter()
    for annotation in annotations:
        targets = {
            str(target)
            for target in annotation.get("target", [])
            if str(target) != NO_TARGET
        }
        votes.update(targets)
    return dict(sorted(votes.items()))


def consensus_targets(
    annotations: Iterable[dict[str, Any]], min_votes: int = 2
) -> tuple[list[str], dict[str, int]]:
    """Return targets supported by at least ``min_votes`` annotators."""
    votes = target_votes(annotations)
    targets = sorted(target for target, count in votes.items() if count >= min_votes)
    return targets, votes


def load_split_lookup(path: str | Path) -> dict[str, str]:
    with Path(path).open(encoding="utf-8") as handle:
        split_ids = json.load(handle)
    return {
        str(post_id): split
        for split, post_ids in split_ids.items()
        for post_id in post_ids
    }


def normalize_post(
    post_id: str,
    post: dict[str, Any],
    split_lookup: dict[str, str],
    target_min_votes: int = 2,
) -> dict[str, Any]:
    annotations = post["annotators"]
    label, label_vote_counts = consensus_label(
        annotation["label"] for annotation in annotations
    )
    targets, target_vote_counts = consensus_targets(
        annotations, min_votes=target_min_votes
    )
    tokens = [str(token) for token in post["post_tokens"]]

    return {
        "post_id": post_id,
        "text": " ".join(tokens),
        "split": split_lookup.get(post_id, "unassigned"),
        "content_label": label,
        "content_label_votes": label_vote_counts,
        "target_labels": targets,
        "target_votes": target_vote_counts,
        "annotator_labels": [
            str(annotation["label"]).lower() for annotation in annotations
        ],
        "annotator_targets": [
            [str(target) for target in annotation.get("target", [])]
            for annotation in annotations
        ],
    }


def iter_hatexplain(
    dataset_path: str | Path,
    split_path: str | Path,
    *,
    include_undecided: bool = False,
    target_min_votes: int = 2,
) -> Iterator[dict[str, Any]]:
    with Path(dataset_path).open(encoding="utf-8") as handle:
        dataset = json.load(handle)
    split_lookup = load_split_lookup(split_path)

    for post_id, post in dataset.items():
        record = normalize_post(
            str(post_id),
            post,
            split_lookup,
            target_min_votes=target_min_votes,
        )
        if include_undecided or record["content_label"] != UNDECIDED:
            yield record


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(records: Iterable[dict[str, Any]], path: str | Path) -> int:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
            count += 1
    return count


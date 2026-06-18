from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Sequence

from .dataset import iter_hatexplain, write_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a consensus JSONL view of HateXplain."
    )
    parser.add_argument(
        "--dataset",
        default="data/raw/hatexplain.json",
        help="Path to the original HateXplain dataset.json file.",
    )
    parser.add_argument(
        "--splits",
        default="data/raw/post_id_divisions.json",
        help="Path to the official split definitions.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/hatexplain.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--include-undecided",
        action="store_true",
        help="Include posts with no majority content label.",
    )
    parser.add_argument(
        "--target-min-votes",
        type=int,
        default=2,
        help="Minimum annotator support for a consensus target label.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records = list(
        iter_hatexplain(
            args.dataset,
            args.splits,
            include_undecided=args.include_undecided,
            target_min_votes=args.target_min_votes,
        )
    )
    count = write_jsonl(records, args.output)

    summary = {
        "records": count,
        "content_labels": dict(
            sorted(Counter(record["content_label"] for record in records).items())
        ),
        "splits": dict(sorted(Counter(record["split"] for record in records).items())),
        "target_labels": dict(
            sorted(
                Counter(
                    target
                    for record in records
                    for target in record["target_labels"]
                ).items()
            )
        ),
        "target_min_votes": args.target_min_votes,
        "include_undecided": args.include_undecided,
    }
    summary_path = Path(args.output).with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {count} records to {args.output}")
    print(f"Wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .inference import TopicClusterer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assign one text to a topic from a fitted BERTopic model."
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Text to classify. If omitted, text is read from standard input.",
    )
    parser.add_argument(
        "--model",
        default="artifacts/bertopic/model",
        help="Saved BERTopic model directory.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.25,
        help="Reject lower-confidence assignments as topic -1.",
    )
    parser.add_argument(
        "--always-assign",
        action="store_true",
        help="Return the nearest topic regardless of confidence.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        raise SystemExit("Input text must not be empty.")

    clusterer = TopicClusterer(
        args.model,
        min_confidence=None if args.always_assign else args.min_confidence,
    )
    print(json.dumps(clusterer.predict(text).to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


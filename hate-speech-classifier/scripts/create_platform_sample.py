from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

FIELDNAMES = [
    "post_id",
    "post_text",
    "country",
    "language",
    "region_area",
    "platform",
    "published_at",
]
REGION_AREAS = [
    "Nicosia",
    "Limassol",
    "Larnaca",
    "Paphos",
    "Famagusta area",
]
PLATFORMS = [
    "Facebook",
    "X/Twitter",
    "Instagram",
    "LinkedIn",
    "TikTok",
    "YouTube",
    "Reddit",
]
STARTED_AT = datetime(2026, 7, 7, tzinfo=timezone.utc)
ENDED_AT = datetime(2026, 7, 20, tzinfo=timezone.utc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a platform-ready CSV sample from processed HateXplain data."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/hatexplain.jsonl"),
        help="Processed HateXplain JSONL input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/hatexplain_platform_sample_5000.csv"),
        help="Complete output CSV.",
    )
    parser.add_argument(
        "--batch-directory",
        type=Path,
        default=Path(
            "data/processed/hatexplain_platform_sample_5000_batches"
        ),
        help="Directory for importer-compatible CSV batches.",
    )
    parser.add_argument("--sample-size", type=int, default=5_000)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260707)
    return parser


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def random_timestamp(rng: random.Random) -> str:
    available_seconds = int((ENDED_AT - STARTED_AT).total_seconds())
    published_at = STARTED_AT + timedelta(
        seconds=rng.randrange(available_seconds)
    )
    return published_at.isoformat().replace("+00:00", "Z")


def build_rows(
    records: list[dict[str, Any]],
    sample_size: int,
    rng: random.Random,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    if sample_size > len(records):
        raise ValueError(
            f"Requested {sample_size} records from a dataset of {len(records)}."
        )

    selected = rng.sample(records, sample_size)
    rows = [
        {
            "post_id": f"hatexplain-{record['post_id']}",
            "post_text": record["text"],
            "country": "Cyprus",
            "language": "English",
            "region_area": rng.choice(REGION_AREAS),
            "platform": rng.choice(PLATFORMS),
            "published_at": random_timestamp(rng),
        }
        for record in selected
    ]
    return rows, selected


def write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_batches(
    directory: Path,
    rows: list[dict[str, str]],
    batch_size: int,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    existing_batches = set(directory.glob("batch_*.csv"))
    batch_paths = []
    for offset in range(0, len(rows), batch_size):
        batch_number = offset // batch_size + 1
        batch_path = directory / f"batch_{batch_number:03d}.csv"
        write_csv(batch_path, rows[offset : offset + batch_size])
        batch_paths.append(batch_path)

    for stale_batch in existing_batches - set(batch_paths):
        stale_batch.unlink()
    return batch_paths


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_rows(rows: list[dict[str, str]], expected_count: int) -> None:
    if len(rows) != expected_count:
        raise ValueError(f"Expected {expected_count} rows, found {len(rows)}.")
    if len({row["post_id"] for row in rows}) != expected_count:
        raise ValueError("Generated post_id values are not unique.")

    for row in rows:
        if list(row) != FIELDNAMES:
            raise ValueError("Generated row does not match the platform schema.")
        if row["country"] != "Cyprus" or row["language"] != "English":
            raise ValueError("Country or language metadata is invalid.")
        if row["region_area"] not in REGION_AREAS:
            raise ValueError("Generated region_area is invalid.")
        if row["platform"] not in PLATFORMS:
            raise ValueError("Generated platform is invalid.")
        published_at = datetime.fromisoformat(
            row["published_at"].replace("Z", "+00:00")
        )
        if not STARTED_AT <= published_at < ENDED_AT:
            raise ValueError("Generated published_at is outside the date range.")
        if not row["post_text"] or len(row["post_text"]) > 4_000:
            raise ValueError("Generated post_text violates importer limits.")


def main() -> int:
    args = build_parser().parse_args()
    if args.sample_size <= 0 or args.batch_size <= 0:
        raise ValueError("Sample and batch sizes must be positive.")

    rng = random.Random(args.seed)
    records = read_jsonl(args.input)
    rows, selected = build_rows(records, args.sample_size, rng)
    validate_rows(rows, args.sample_size)

    write_csv(args.output, rows)
    batch_paths = write_batches(args.batch_directory, rows, args.batch_size)
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest = {
        "source": str(args.input),
        "output": str(args.output),
        "records": len(rows),
        "seed": args.seed,
        "date_range": {
            "start_inclusive": STARTED_AT.isoformat().replace("+00:00", "Z"),
            "end_inclusive": "2026-07-19T23:59:59Z",
        },
        "content_labels": dict(
            sorted(Counter(record["content_label"] for record in selected).items())
        ),
        "regions": dict(
            sorted(Counter(row["region_area"] for row in rows).items())
        ),
        "platforms": dict(
            sorted(Counter(row["platform"] for row in rows).items())
        ),
        "upload_batches": {
            "directory": str(args.batch_directory),
            "batch_size": args.batch_size,
            "files": len(batch_paths),
        },
        "sha256": sha256(args.output),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(rows)} rows to {args.output}")
    print(f"Wrote {len(batch_paths)} upload batches to {args.batch_directory}")
    print(f"Wrote manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

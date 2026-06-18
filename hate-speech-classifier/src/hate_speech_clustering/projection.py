from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np


@dataclass(frozen=True)
class ProjectionPoint:
    x: float
    y: float


class TopicProjector:
    """Transform model embeddings into a fixed, comparable 2D space."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        artifact = joblib.load(self.path)
        self.projector = artifact["projector"]
        self.metadata = artifact["metadata"]

    def transform(self, embeddings: np.ndarray) -> list[ProjectionPoint]:
        coordinates = self.projector.predict(np.asarray(embeddings))
        return [
            ProjectionPoint(x=float(point[0]), y=float(point[1]))
            for point in coordinates
        ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fit and save a stable 2D UMAP projection for the API."
    )
    parser.add_argument(
        "--model",
        default="artifacts/bertopic-full/model",
    )
    parser.add_argument(
        "--documents",
        default="artifacts/bertopic-full/document_topics_labeled.csv",
    )
    parser.add_argument(
        "--output",
        default="artifacts/bertopic-full/projection_2d.joblib",
    )
    parser.add_argument(
        "--coordinates-output",
        default="artifacts/bertopic-full/projection_2d.csv",
    )
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--min-dist", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--embedding-model",
        default="artifacts/bertopic-full/embedding_model",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    import pandas as pd
    from bertopic import BERTopic
    from sklearn.neighbors import KNeighborsRegressor
    from umap import UMAP

    documents = pd.read_csv(args.documents)
    if "text" not in documents:
        raise SystemExit(f"{args.documents} does not contain a text column")

    topic_model = BERTopic.load(
        args.model,
        embedding_model=args.embedding_model,
    )
    texts = documents["text"].astype(str).tolist()
    embeddings = topic_model._extract_embeddings(
        texts,
        method="document",
        verbose=True,
    )
    projector = UMAP(
        n_neighbors=args.n_neighbors,
        n_components=2,
        min_dist=args.min_dist,
        metric="cosine",
        random_state=args.seed,
        transform_seed=args.seed,
    )
    coordinates = projector.fit_transform(embeddings)
    interpolation_model = KNeighborsRegressor(
        n_neighbors=args.n_neighbors,
        weights="distance",
        algorithm="brute",
        metric="cosine",
        n_jobs=1,
    )
    interpolation_model.fit(
        np.asarray(embeddings, dtype=np.float32),
        np.asarray(coordinates, dtype=np.float32),
    )

    metadata: dict[str, Any] = {
        "projection_version": "hatexplain-umap-2d-2026-06-13",
        "model_path": str(args.model),
        "embedding_model": args.embedding_model,
        "document_count": len(documents),
        "embedding_dimensions": int(np.asarray(embeddings).shape[1]),
        "n_neighbors": args.n_neighbors,
        "min_dist": args.min_dist,
        "metric": "cosine",
        "api_projection_method": "cosine_knn_interpolation_into_umap",
        "interpolation_neighbors": args.n_neighbors,
        "seed": args.seed,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"projector": interpolation_model, "metadata": metadata},
        output_path,
        compress=3,
    )

    projected_documents = documents.copy()
    projected_documents["x"] = coordinates[:, 0]
    projected_documents["y"] = coordinates[:, 1]
    coordinates_path = Path(args.coordinates_output)
    coordinates_path.parent.mkdir(parents=True, exist_ok=True)
    projected_documents.to_csv(coordinates_path, index=False)

    metadata_path = output_path.with_suffix(".json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote 2D projector to {output_path}")
    print(f"Wrote {len(documents)} coordinates to {coordinates_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

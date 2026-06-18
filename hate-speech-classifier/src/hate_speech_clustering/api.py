from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Callable

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, field_validator

from .service import SemanticClusteringService, ServiceSettings


class PredictionRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=5000)]

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be blank")
        return normalized


class Keyword(BaseModel):
    term: str
    weight: float


class Coordinates(BaseModel):
    x: float
    y: float
    projection_version: str


class CandidateCategory(BaseModel):
    topic_id: int
    parent_category: str | None
    category: str | None


class PredictionResponse(BaseModel):
    text: str
    topic_id: int
    parent_category: str | None
    category: str | None
    confidence: float | None
    is_outlier: bool
    assignment_method: str
    keywords_role: str
    keywords: list[Keyword]
    keywords_topic_id: int
    coordinates: Coordinates
    nearest_candidate: CandidateCategory


def settings_from_environment() -> ServiceSettings:
    root = Path(
        os.environ.get(
            "HSC_ARTIFACT_DIR",
            "artifacts/bertopic-full",
        )
    )
    return ServiceSettings(
        model_path=Path(os.environ.get("HSC_MODEL_PATH", root / "model")),
        embedding_model_path=Path(
            os.environ.get(
                "HSC_EMBEDDING_MODEL_PATH",
                root / "embedding_model",
            )
        ),
        projection_path=Path(
            os.environ.get(
                "HSC_PROJECTION_PATH",
                root / "projection_2d.joblib",
            )
        ),
        topic_metadata_path=Path(
            os.environ.get(
                "HSC_TOPIC_METADATA_PATH",
                root / "topic_labels.json",
            )
        ),
        min_confidence=float(os.environ.get("HSC_MIN_CONFIDENCE", "0.25")),
    )


def create_app(
    service_factory: Callable[[], Any] | None = None,
) -> FastAPI:
    factory = service_factory or (
        lambda: SemanticClusteringService(settings_from_environment())
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.clustering_service = factory()
        yield

    application = FastAPI(
        title="Hate-Speech Semantic Clustering API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.get("/health")
    async def health(request: Request) -> dict[str, str]:
        service = request.app.state.clustering_service
        return {
            "status": "ok",
            "projection_version": service.projection_version,
        }

    @application.post("/predict", response_model=PredictionResponse)
    async def predict(
        payload: PredictionRequest,
        request: Request,
    ) -> dict:
        service = request.app.state.clustering_service
        return service.predict(payload.text)

    return application


app = create_app()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Serve the semantic clustering FastAPI application."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HSC_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("HSC_PORT", "8000")),
    )
    args = parser.parse_args()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

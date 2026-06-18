FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HSC_HOST=0.0.0.0 \
    HSC_PORT=8000 \
    HSC_ARTIFACT_DIR=/app/artifacts/bertopic-full

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.9.1" \
    && pip install --no-cache-dir .

ENV NUMBA_CACHE_DIR=/tmp/numba-cache

RUN addgroup --system app && adduser --system --ingroup app app

COPY --chown=app:app artifacts/bertopic-full/model ./artifacts/bertopic-full/model
COPY --chown=app:app artifacts/bertopic-full/embedding_model ./artifacts/bertopic-full/embedding_model
COPY --chown=app:app artifacts/bertopic-full/projection_2d.joblib ./artifacts/bertopic-full/projection_2d.joblib
COPY --chown=app:app artifacts/bertopic-full/topic_labels.json ./artifacts/bertopic-full/topic_labels.json

USER app

EXPOSE 8000

CMD ["serve-cluster-api"]

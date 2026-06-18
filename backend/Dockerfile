FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

RUN addgroup --system app && adduser --system --ingroup app app

COPY --chown=app:app alembic.ini .
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.seed_demo_data && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

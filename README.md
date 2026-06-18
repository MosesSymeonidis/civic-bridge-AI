# Civic Bridge AI

Starter monorepo with a FastAPI backend, PostgreSQL, a RAG API, a hate-speech
semantic classifier, and a React/Vite frontend. Docker Compose builds the
application services, runs database migrations, loads synthetic dashboard
records for the demo, serves the frontend with Nginx, and proxies frontend API
requests to the application services.

## Live instance

The application is available at http://34.65.145.212:3000/.

## Structure

```text
.
|-- backend/          FastAPI application and tests
|-- civic-bridge-ai-rag/       Incident analysis and response service
|-- frontend/         React, TypeScript, Vite, and Nginx
|-- hate-speech-classifier/    Semantic clustering API and model artifacts
|-- compose.yaml      Server service orchestration
|-- compose.local.yaml Local development overrides
|-- .env              Environment-specific settings (ignored by Git)
`-- .env.example      Environment variable template
```

## Run with Docker

For local development, use the local override so PostgreSQL data and
credentials remain independent from the server:

```bash
docker compose -f compose.yaml -f compose.local.yaml up --build
```

The equivalent shortcut is `make up`.

The optional `LOCAL_POSTGRES_*` values in `.env` control only the local
database. They default to the development values shown in `.env.example`.

Open:

- Frontend: http://localhost:3000
- Student workspace: http://localhost:3000/students
- Educator workspace: http://localhost:3000/educators
- Public Institutions dashboard: http://localhost:3000/public-institutions
- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health
- RAG API: http://localhost:8001
- Hate-speech classifier API: http://localhost:8002
- Classifier OpenAPI docs: http://localhost:8002/docs
- Classifier health check: http://localhost:8002/health

The frontend proxy exposes the classifier at
`http://localhost:3000/classifier-api/`. For example:

```bash
curl -X POST http://localhost:3000/classifier-api/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"Text to assign to a semantic cluster"}'
```

Stop the stack with:

```bash
docker compose -f compose.yaml -f compose.local.yaml down
```

On the server, continue using the unchanged server configuration:

```bash
docker compose -f compose.yaml up --build -d
```

Compose leaves demo data disabled by default, so the dashboard only shows
records stored by the application. On backend startup, any older records
tagged `synthetic-demo-v1` or `synthetic-cluster-demo-v1` are removed. To
explicitly load synthetic demo records, start the stack with:

```bash
SEED_DEMO_DATA=true docker compose -f compose.yaml -f compose.local.yaml up --build
```

When enabled, each backend start refreshes only records tagged
`synthetic-demo-v1`; completed user discussions are not modified.

## Run locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

This expects PostgreSQL at the `DATABASE_URL` configured in `.env`. Running
`docker compose -f compose.yaml -f compose.local.yaml up postgres` is
sufficient when developing the backend outside Docker.

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` requests to
`http://localhost:8000`.

To populate a locally configured database without restarting Compose:

```bash
make backend-seed
```

## Checks

```bash
cd backend && pytest
cd hate-speech-classifier && pytest
cd frontend && npm run check
docker compose -f compose.yaml config
docker compose -f compose.yaml -f compose.local.yaml config
```

Copy `.env.example` when creating environment-specific configuration. Keep
secrets out of `.env.example` and source control.
Set `VITE_SOCIAL_POST_PAGE_URL` to control the link appended to generated
social media posts.

## Student conversation API

Create a context session:

```http
POST /api/v1/students/sessions
Content-Type: application/json

{
  "country": "Cyprus",
  "region_area": "Nicosia",
  "language": "English",
  "age_band": "14-17"
}
```

Send a message using the returned `session_id`:

```http
POST /api/v1/chat
Content-Type: application/json

{
  "session_id": "{session_id}",
  "participant_type": "student",
  "message": "Describe the incident here without identifying details."
}
```

Active chat sessions currently use in-memory storage and reset when the
backend restarts. Completed discussion analytics are persisted in PostgreSQL.
The response service is a deterministic, context-aware placeholder for a
future LLM provider; the API contract already passes the stored student
context into every response.

## Educator conversation API

Create an educator context session:

```http
POST /api/v1/educators/sessions
Content-Type: application/json

{
  "country": "Cyprus",
  "region_area": "Nicosia",
  "language": "English",
  "educator_role": "classroom-teacher",
  "learner_age_band": "14-17",
  "education_setting": "secondary-school",
  "support_goal": "classroom-activity"
}
```

Send a message using the returned `session_id`:

```http
POST /api/v1/chat
Content-Type: application/json

{
  "session_id": "{session_id}",
  "participant_type": "educator",
  "message": "Describe the incident or educational need."
}
```

The educator context is included in every response-generation call. Active
educator sessions use the same in-memory, provider-independent approach as
student sessions, while completed analytics are persisted.

## Chat API

`POST /api/v1/chat` is the shared message endpoint for student and educator
sessions. It validates the participant type against the session and returns:

```json
{
  "session_id": "00000000-0000-0000-0000-000000000000",
  "participant_type": "student",
  "assistant_message": "Placeholder response"
}
```

The endpoint currently dispatches to deterministic local placeholder services.
It contains no OpenAI client, credentials, model selection, or external model
call. The existing role-specific message endpoints remain available for
backward compatibility.

Before either chat workspace calls `POST /api/v1/chat`, the frontend
anonymizes the message in the browser. It combines regex detection for common
contact details with the
`onnx-community/piiranha-v1-detect-personal-information-ONNX` token
classification model and the
`onnx-community/bert-base-multilingual-cased-ner-hrl-ONNX` person-name model,
both running through `@huggingface/transformers`. Placeholder mappings are
scoped to the active session, so repeated values receive the same replacement.
The original message is retained only in the local UI; if either browser model
cannot load or run, the chat request is not sent. The quantized models are
downloaded on first use and then use the browser cache.

After the RAG chat accepts the anonymized message, the frontend also submits
that anonymized text to `POST /classifier-api/predict`. The resulting topic,
parent category, confidence, keywords, and fixed two-dimensional coordinates
are stored through the participant session API:

```http
POST /api/v1/students/sessions/{session_id}/classifications
POST /api/v1/educators/sessions/{session_id}/classifications
```

The backend deliberately rejects the classifier response's `text` field and
stores only structured model output plus coarse session context. RAG and
semantic-classifier records share an idempotency event ID but remain
independent, so one pipeline can succeed when the other is unavailable.

## Discussion completion API

When the analysis pipeline finishes a student or educator discussion, submit
its structured output to the corresponding completion endpoint:

```http
POST /api/v1/students/sessions/{session_id}/complete
POST /api/v1/educators/sessions/{session_id}/complete
Content-Type: application/json

{
  "severity": "potential-hate-speech",
  "semantic_barriers": ["stigma", "collective-blame"],
  "bridge_promoters": ["outgroup-empathy"],
  "constructive_response": true,
  "reviewer_outcome": "bridge-response-adapted",
  "analysis_version": "prototype-v1"
}
```

The backend copies country, coarse region, language, age band, participant
type, and educator context from the session. It derives incident and
human-review flags from severity and stores the participant messages available
in the session for the review queue. A session can only be completed once.

## Public Institutions dashboard

The `/public-institutions` workspace presents a responsive, privacy-preserving
dashboard and loads every visualization from the backend summary API:

```http
GET /api/v1/dashboard/summary?time_range=30d&country=Cyprus&language=English&participant_type=student
```

Supported time ranges are `30d`, `90d`, and `12m`. All filters are optional.
The response includes totals, incident trends, source, region, severity,
semantic barriers, bridge promoters, semantic-cluster coordinates, age bands,
languages, and reviewer outcomes. The dashboard renders classifier coordinates
as a two-dimensional scatterplot with topic, parent-category, and keyword
tags. It displays only topics meeting `DASHBOARD_MINIMUM_GROUP_SIZE` and never
mixes points from different projection versions; the default threshold is one
so each stored event is reflected immediately.

Review-required incidents are available through the institution dashboard
with their anonymized incident text and structured analysis:

```http
GET /api/v1/dashboard/reviews?reviewed=false&time_range=30d&country=Cyprus
PATCH /api/v1/dashboard/reviews/{incident_id}
```

The review action records a reviewer reference, optional notes, and an audit
timestamp. Completed actions move from the Pending queue to Reviewed and
update the dashboard review metrics immediately.

### Social media CSV import

The institution dashboard includes an **Import social media CSV** button. The
CSV file must use these columns:

| Column | Required | Description |
| --- | --- | --- |
| `post_id` | Yes | Stable, unique source identifier; maximum 200 characters |
| `post_text` | Yes | Post content to analyze; maximum 4,000 characters |
| `country` | Yes | Country used by incident analysis and dashboard filters |
| `language` | Yes | Language used by dashboard filters |
| `region_area` | No | Coarse region; defaults to `Unspecified` |
| `platform` | No | Source platform, such as `mastodon` or `bluesky` |
| `published_at` | No | ISO 8601 timestamp |
| `source_reference` | No | External source reference or URL |

Imports support up to 10,000 rows and 50 MB per file. The browser checks
duplicates in bounded batches, then processes rows sequentially and reports
aggregate progress with recent row outcomes. Each `post_text` is anonymized
locally; only the anonymized content is sent to the incident-analysis and
semantic-classifier APIs. The anonymized text and structured outputs are
stored for the human review queue. The original post content is not sent to
the backend database API or persisted. Reusing a `post_id` safely skips the
duplicate.

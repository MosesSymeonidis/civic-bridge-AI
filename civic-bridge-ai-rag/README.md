# Civic Bridge AI RAG

Civic Bridge AI RAG is a FastAPI demo service for understanding and responding
to hate-speech incidents using Council of Europe standards. It combines a small
static web chat UI, retrieval over curated legal/policy sources, structured
two-axis analysis, role- and age-conditioned guidance, and country-specific
support/reporting contacts.

The system is designed as a human-review aid. It does not make legal
determinations, submit reports to authorities, or replace trained judgment.

## What It Does

- Classifies shared content into a four-tier risk signal model grounded in
  Council of Europe Recommendation CM/Rec(2022)16.
- Detects semantic-barrier mechanisms from the local codebook and suggests
  dialogue-supporting promoters.
- Provides teacher/student chat guidance with age bands: `6-9`, `10-13`,
  `14-17`, and `18+`.
- Runs a student safety triage path before analysis when a student appears to
  be personally targeted.
- Retrieves source passages from a Chroma legal corpus and exposes clickable
  source references.
- Shows country-specific support/reporting contacts when escalation is
  requested.
- Creates local incident-report drafts in SQLite for human review.

## Repository Layout

```text
app/
  main.py              FastAPI app, API routes, static file mount
  chat.py              Conversation orchestration and reporting-context injection
  classify.py          Structured two-axis analysis
  retrieval.py         Chroma retrieval and source citation formatting
  llm.py               LiteLLM completion/embedding wrapper
  registry.py          Country contacts and related ECHR case lookup
  reports.py           Local SQLite report draft store
  safety.py            Triage, age gating, and legal-determination softening
  prompts/             Base, role, age-band, and triage prompts
  static/index.html    Single-file browser chat UI

data/
  knowledge/           Curated JSON/YAML knowledge files
  raw/legal/           Source PDFs used by the index builder
  index/chroma/        Local Chroma persistent index

ingest/
  build_index.py       PDF chunking, embedding, and Chroma upsert
  fetch_legal.py       Helper for fetching CM/Rec(2022)16
  scrape_cases.py      FSF/Infogram case extraction
  enrich_cases.py      HUDOC enrichment and theme tagging
  build_registry.py    Council of Europe country registry builder

tests/                 Pytest coverage for API, chat, retrieval, ingestion, safety
```

## Requirements

- Python 3.10+
- `uv`
- At least one LiteLLM-compatible chat model configured for normal LLM use
- An embedding model configured for index building and retrieval

Dependencies are declared in `pyproject.toml`. The default model settings are in
`app/config.py`:

- `CBA_MODEL_CHAIN`: defaults to
  `openai/gpt-4.1,anthropic/claude-sonnet-4-6,ollama/llama3.1`
- `CBA_VISION_MODEL_CHAIN`: defaults to
  `openai/gpt-4.1,anthropic/claude-sonnet-4-6` for image-to-text chat uploads
- `CBA_EMBED_MODEL`: defaults to `openai/text-embedding-3-small`

Put provider credentials in a local `.env` file as required by LiteLLM, for
example `OPENAI_API_KEY=...`.

## Quick Start

Install dependencies:

```bash
uv sync
```

Run the API and web UI:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the browser UI at:

```text
http://localhost:8000/
```

For development with automatic reload:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Overview

### `GET /healthz`

Returns service health:

```json
{"status": "ok"}
```

### `POST /analyze`

Runs structured analysis on supplied text.

Request:

```json
{
  "text": "Text to analyze",
  "country": "Cyprus",
  "age_band": "14-17",
  "role": "teacher"
}
```

Response shape is `AnalysisResult` from `app/classify.py`, including:

- `tier`
- `tier_label`
- `rationale`
- `barriers`
- `target_group`
- `themes`
- `related_cases`
- `routing`

### `POST /chat`

Runs the role/age/country-conditioned conversation flow.

Request:

```json
{
  "session_id": "demo-session",
  "role": "teacher",
  "age_band": "14-17",
  "country": "Cyprus",
  "message": "A student showed me this...",
  "attachment": "Optional explicit content to analyze"
}
```

Response includes:

- `reply`: assistant text
- `analysis`: structured analysis card data, or `null`
- `citations`: retrieved source references
- `reporting`: country support/reporting contacts when requested
- `triage`: whether the deterministic student triage path handled the turn

### `GET /registry/{country}`

Returns configured reporting/support contacts for a country. Cyprus is
hand-verified; many other Council of Europe states are currently stubs unless
populated by the registry builder.

### `POST /report`

Creates a local report draft in `data/reports.db`. This does not submit to any
authority.

Request:

```json
{
  "text": "Reported content",
  "country": "Cyprus",
  "role": "teacher",
  "tier": 3,
  "tier_label": "potential hate speech for human review",
  "rationale": []
}
```

## Conversation Flow

`app/chat.py` coordinates each turn:

1. Extract quoted or attached third-party content.
2. Run student triage before any LLM call when a student may be personally
   targeted.
3. Analyze resolved content with `app/classify.py`.
4. Otherwise retrieve top-k legal/policy passages with `app/retrieval.py`.
5. Build a system prompt from `app/prompts/`.
6. Call the LLM once.
7. Soften direct legal determinations before returning.

Sessions are stored in the process-local `SESSIONS` dict. Restarting the server
clears chat history.

## Structured Analysis

`app/classify.py` performs one structured LLM call and deterministic
post-processing:

- Severity tiers:
  - `1`: ordinary political expression
  - `2`: offensive or harmful expression
  - `3`: potential hate speech for human review
  - `4`: high-severity incitement/dehumanisation risk
- Semantic-barrier findings are filtered to known codebook IDs.
- Citation IDs are filtered to the visible norms-core allowlist.
- Case themes are filtered to the supported ECHR theme vocabulary.
- Severe example spans are redacted for under-13 users.
- Tier 3/4 analyses can attach country routing data.

## Retrieval and Sources

The retrieval index is a local Chroma collection named `legal_corpus` at
`data/index/chroma`. The index contains chunks from PDFs under
`data/raw/legal/`. Source document metadata and canonical URLs live in
`app/source_documents.py`.

To rebuild the index:

```bash
uv run python ingest/build_index.py
```

This reads PDFs, chunks page text, embeds chunks with `CBA_EMBED_MODEL`, and
upserts them into Chroma with `doc_id`, `title`, `page`, and `url` metadata.

The web UI renders retrieved source references as collapsed clickable
`Sources (n)` disclosures.

## Knowledge Data

The checked-in knowledge files are:

- `data/knowledge/norms_core.yaml`: curated Council of Europe passages and
  tier labels.
- `data/knowledge/codebook.json`: semantic-barrier mechanisms and promoters.
- `data/knowledge/cases.json`: ECHR hate-speech case metadata and themes.
- `data/knowledge/authorities.json`: country support/reporting contacts.

Ingestion/enrichment helpers can regenerate or update some of this data, but
committed manual corrections may be lost if source files are regenerated
without diff review. See comments in `ingest/enrich_cases.py`.

## Frontend

The UI is a single static file at `app/static/index.html`.

It supports:

- role selection: `student` or `teacher`
- age-band selection
- country selection
- chat messages and multiline paste
- collapsed analysis cards
- collapsed country reporting cards
- collapsed clickable source citations

Because the app mounts `StaticFiles` at `/`, API routes must be registered
before the static mount.

## Safety and Privacy

Safety controls are enforced in code as well as prompts:

- Student triage runs before LLM analysis when first-person targeting/distress
  indicators appear.
- Quoted/attached harmful content is stripped before student triage checks to
  avoid treating the harasser's words as the student's own distress.
- Severe-tier example spans are redacted for `6-9` and `10-13`.
- Output is post-processed to soften direct claims such as "is illegal".
- Prompts instruct the assistant not to request usernames, account IDs, profile
  links, exact locations, school names, or names of minors.

## Tests

Run the full suite:

```bash
uv run pytest -q
```

The suite covers API routes, chat orchestration, classification post-processing,
retrieval formatting, data ingestion helpers, registry behavior, report drafts,
prompt composition, safety controls, and static frontend expectations.

## Development Notes

- Use `--reload` while editing backend Python or prompt files.
- If the server is running without `--reload`, restart it after code changes.
- Refresh the browser after changing `app/static/index.html`.
- Rebuild the Chroma index after changing source PDFs or source metadata if the
  index should persist those changes directly.
- Retrieval has a runtime URL fallback by `doc_id`, so clickable source URLs can
  work with older index metadata.

## Known Issues

- `GET /norms` is intended to expose curated norms passages, but `app/main.py`
  currently references `norms.load_norms()` without importing `norms`.
- The project is demo-scoped: sessions are in-memory, report drafts are local,
  and no production authentication or authority-submission flow is implemented.
- Most country registry entries are stubs unless enriched or hand-verified.

## Project Status

This is an in-development hackathon/demo project. Treat outputs as guidance for
human review, not as legal advice or automated enforcement.

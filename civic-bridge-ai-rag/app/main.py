from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import chat, classify, image_text, norms, registry, reports, stats
from app.config import ROOT

app = FastAPI(title="Civic Bridge AI RAG Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # keep allow_credentials=False (default) -- wildcard origins + credentials
    # is a footgun; leave this explicit for post-demo auth hardening
    allow_credentials=False,
)

AgeBand = Literal["6-9", "10-13", "14-17", "18+", "mixed"]
Role = Literal["student", "teacher"]


class AnalyzeIn(BaseModel):
    text: str
    country: Optional[str] = None
    age_band: Optional[AgeBand] = None
    role: Optional[Role] = None


class ChatImageIn(BaseModel):
    image: str
    filename: Optional[str] = Field(default=None, max_length=255)
    mime_type: Optional[str] = Field(default=None, max_length=120)


class ChatIn(BaseModel):
    session_id: str
    role: Role
    age_band: AgeBand
    country: str
    message: str
    attachment: Optional[str] = None
    image: Optional[ChatImageIn] = None
    mode: Optional[str] = None


class ReportIn(BaseModel):
    text: str
    country: str
    role: Role
    tier: int = Field(ge=1, le=4)
    tier_label: str
    rationale: list[dict] = []


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/norms")
def get_norms():
    """The curated CoE passages, keyed by citation ID, so clients can resolve
    [citation-id] references in replies to the actual source text."""
    return {p["id"]: {"source": p["source"], "text": p["text"]}
            for p in norms.load_norms()["passages"]}


@app.get("/registry/{country}")
def get_registry(country: str):
    try:
        return registry.authorities(country)
    except KeyError:
        raise HTTPException(404, f"unknown country: {country}")


@app.get("/stats")
def get_stats():
    """Aggregated awareness statistics: categorical signals only, no content."""
    return stats.aggregate()


@app.post("/analyze", response_model=classify.AnalysisResult)
def post_analyze(body: AnalyzeIn):
    result = classify.analyze(body.text, country=body.country,
                              age_band=body.age_band, role=body.role)
    stats.record(tier=result.tier, barriers=[b.id for b in result.barriers],
                 themes=result.themes, country=body.country, role=body.role,
                 age_band=body.age_band)
    return result


@app.post("/chat")
def post_chat(body: ChatIn):
    attachment = body.attachment
    if body.image is not None:
        try:
            image_attachment = image_text.extract_text(
                body.image.image,
                mime_type=body.image.mime_type,
                user_prompt=body.message,
            )
        except image_text.ImageTextError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except image_text.ImageTextUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        attachment = (
            f"{attachment}\n\n{image_attachment}"
            if attachment
            else image_attachment
        )

    return chat.handle(session_id=body.session_id, role=body.role,
                       age_band=body.age_band, country=body.country,
                       message=body.message, attachment=attachment,
                       mode=body.mode)


@app.post("/report")
def post_report(body: ReportIn):
    return reports.create_report(text=body.text, country=body.country,
                                 role=body.role, tier=body.tier,
                                 tier_label=body.tier_label,
                                 rationale=body.rationale)


# StaticFiles must be mounted LAST -- it acts as a catch-all and would shadow
# API routes if registered earlier.
app.mount("/", StaticFiles(directory=str(ROOT / "app" / "static"), html=True),
          name="static")

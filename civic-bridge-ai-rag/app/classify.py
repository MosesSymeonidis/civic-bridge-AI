"""Two-axis analysis: CM/Rec(2022)16 severity + semantic barriers.

One structured LLM call grounded in the curated norms core and the full
codebook; everything after the call is deterministic code.
"""
from pydantic import BaseModel, Field

from app import codebook, llm, norms, registry, safety

CASE_THEMES = [
    "Ethnic Hatred", "Anti-semitism", "Genocide Denial", "LGBTQ",
    "Religious Hatred", "Blasphemy", "Totalitarianism", "Defamation",
    "Totalitarian symbols", "Violence", "Apology",
    "Violence and religious intolerance", "Violence and terrorism",
]


class CitationRef(BaseModel):
    citation_id: str
    reason: str


class BarrierFinding(BaseModel):
    id: str
    span: str
    rationale: str
    promoters: list[str] = []


class LLMAnalysis(BaseModel):
    tier: int = Field(ge=1, le=4)
    rationale: list[CitationRef]
    barriers: list[BarrierFinding]
    target_group: str
    themes: list[str] = []
    confidence: str = "medium"


class AnalysisResult(LLMAnalysis):
    tier_label: str = ""
    related_cases: list[dict] = []
    routing: dict | None = None


SYSTEM_TEMPLATE = """You are the analysis engine of Civic Bridge AI, a Council of
Europe hackathon project. You produce risk-support signals for trained human review.
You NEVER determine legality; that belongs to authorities and courts.

Assess the text on two independent axes.

AXIS 1, SEVERITY. Place the text in exactly one tier:
1 = ordinary political expression (protected, even if critical or unpleasant; discusses policy, events, or general grievances without targeting a group)
2 = offensive or harmful expression (lawful but harmful; includes stereotyping, hostile generalisations about groups, suppression of a community's narrative or voice, or discourse manipulation that does not yet reach the threshold of hate speech)
3 = potential hate speech for human review (denigrates a protected group; attributes inherent negative traits or essentialises a group as untrustworthy, unchangeable, or inferior, but WITHOUT explicit calls for violence, expulsion, or elimination, and without dehumanising metaphors)
4 = high-severity incitement/dehumanisation risk (explicitly incites violence or expulsion; dehumanises using animal, vermin, pest, or disease metaphors; or directly calls for a group to be driven out, exterminated, or harmed)
Anchor every step of your reasoning to the passages below, citing ONLY IDs that appear
in the passages. The valid citation IDs are exactly: {citation_ids}

COUNCIL OF EUROPE PASSAGES:
{norms}

AXIS 2, SEMANTIC BARRIERS. Detect which of these dialogue-blocking mechanisms appear.
Quote the exact triggering span verbatim from the text. Only use barrier IDs from this codebook:
{codebook}

Respond with JSON only:
{{"tier": <1-4>, "rationale": [{{"citation_id": "...", "reason": "..."}}],
"barriers": [{{"id": "...", "span": "...", "rationale": "..."}}],
"target_group": "...", "themes": [<subset of {themes}>], "confidence": "low|medium|high"}}"""


def analyze(text: str, country: str | None = None,
            age_band: str | None = None, role: str | None = None) -> AnalysisResult:
    # `role` is accepted for API symmetry with the chat layer (Task 15) and
    # reserved for role-conditioned analysis; it does not affect analysis yet.
    #
    # The citation allowlist must match what norms_block() actually shows the
    # model: system-tagged passages are excluded from the prompt, so citing
    # them would be a citation without visible text behind it.
    valid_citations = [p["id"] for p in norms.load_norms()["passages"]
                       if "system" not in p.get("tags", [])]
    system = SYSTEM_TEMPLATE.format(
        norms=norms.norms_block(), codebook=codebook.codebook_block(),
        themes=CASE_THEMES, citation_ids=valid_citations,
    )
    raw: LLMAnalysis = llm.complete(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"TEXT TO ANALYSE:\n{text}"}],
        schema=LLMAnalysis,
    )

    # Deterministic post-processing. The model's structured output is treated as
    # a set of candidate signals; auditability depends on every retained citation,
    # barrier, and theme being a real ID from the curated knowledge.

    # 1. Drop unknown barrier IDs; attach promoters to the survivors.
    known_barriers = set(codebook.load_codebook()["barriers"])
    barriers = []
    for finding in raw.barriers:
        if finding.id not in known_barriers:
            continue
        finding.promoters = codebook.promoters_for(finding.id)
        barriers.append(finding)

    # 2. Age-gate barrier spans (redacts severe-tier examples for under-13s).
    spans = safety.gate_spans([b.span for b in barriers], raw.tier, age_band)
    for finding, span in zip(barriers, spans):
        finding.span = span

    # 3. Drop invented citation IDs that are not in the norms core.
    valid_citation_set = set(valid_citations)
    rationale = [c for c in raw.rationale if c.citation_id in valid_citation_set]

    # 4. Enforce the theme vocabulary before the cases lookup.
    case_themes = set(CASE_THEMES)
    themes = [t for t in raw.themes if t in case_themes]

    result = AnalysisResult(**{
        **raw.model_dump(),
        "barriers": [b.model_dump() for b in barriers],
        "rationale": [c.model_dump() for c in rationale],
        "themes": themes,
    })
    result.tier_label = norms.tier_label(raw.tier)
    result.related_cases = registry.cases_by_theme(themes) if themes else []
    if raw.tier >= 3 and country:
        try:
            result.routing = {"authorities": registry.authorities(country),
                              "can_report": True}
        except KeyError:
            result.routing = None
    return result

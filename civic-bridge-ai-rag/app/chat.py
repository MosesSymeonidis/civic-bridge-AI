"""Conversation orchestration: triage first, then analysis or retrieval, one
LLM completion, output guard. Sessions are in-memory (demo scope).

The flow per turn is explicit and deterministic:
  1. Deterministic quote extraction: a quoted block ("..." or > lines) in the
     message is treated as a pasted post, no LLM involved.
  2. STUDENT messages pass the rule-based triage screen, on the message MINUS
     any quoted segment (the harasser's words inside a quote must not trigger
     the student's own safety pivot). A trigger returns the deterministic triage
     template (no LLM, cannot fail) and pins the session to state="triage".
     Once in triage state, subsequent messages do NOT re-trigger.
  3. Post resolution: explicit attachment > quoted block > one small LLM
     extraction call with a verbatim-substring guard (app.extract).
  4. A resolved post runs classify.analyze, injected as grounding context;
     otherwise retrieve top-k chunks for grounding.
  5. One LLM completion with the persona system prompt + context + history.
  6. Output passes safety.soften_determinations.

SESSIONS is a process-local dict by design: this is a single-instance hackathon
demo with no persistence requirement. Restarting the server clears all chats.
"""
import json
import re

from app import (
    classify,
    extract,
    llm,
    norms,
    personas,
    registry,
    retrieval,
    safety,
    source_documents,
    stats,
)

SESSIONS: dict[str, dict] = {}
MAX_TURNS = 20

_TARGETED_NOTE = (
    "\n\nNote: this student earlier indicated they may be personally targeted. "
    "Stay gentle, keep help-seeking visible, and do not push analysis unless "
    "they ask for it."
)


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.findall(r"[^.!?]+[.!?]+(?=\s|$)|[^.!?]+$", text)
        if sentence.strip()
    ]


def _fallback_summary(reply: str) -> str:
    plain = re.sub(r"```[\s\S]*?```", " ", reply)
    plain = re.sub(r"`([^`]+)`", r"\1", plain)
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain)
    plain = re.sub(r"^#{1,6}\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"^\s{0,3}[-*+]\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"^\s{0,3}\d+\.\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"[*_~>#]", "", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    summary = " ".join(_sentences(plain)[:2]) or plain
    if len(summary) <= 320:
        return summary
    return f"{summary[:317].rsplit(' ', 1)[0]}..."


def _generated_summary(reply: str, role: str, age_band: str) -> str:
    prompt = [
        {
            "role": "system",
            "content": (
                "Summarize the Civic Bridge answer for display above a full "
                "report. Use 1-2 concise sentences. Preserve the main support "
                "or action guidance. Do not add facts that are not in the "
                "answer. Do not use markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Audience role: {role}; age band: {age_band}.\n\n"
                f"Full answer:\n{reply}"
            ),
        },
    ]
    try:
        summary = safety.soften_determinations(
            llm.complete(prompt, temperature=0)
        )
    except Exception:
        return _fallback_summary(reply)

    summary = re.sub(r"\s+", " ", summary).strip().strip('"')
    sentences = _sentences(summary)
    if len(sentences) > 2:
        summary = " ".join(sentences[:2])
    return summary or _fallback_summary(reply)


def _session(session_id: str) -> dict:
    return SESSIONS.setdefault(session_id, {"history": [], "state": "normal"})


def _reporting_requested(message: str) -> bool:
    text = message.lower()
    return bool(
        re.search(r"\b(option\s*)?c\)?\.?\b", text)
        or any(word in text for word in (
            "report", "reporting", "escalate", "escalation", "official",
            "authority", "authorities", "police", "hotline", "helpline",
            "ombudsman", "cybersafety",
        ))
    )


def _country_reporting(country: str) -> dict | None:
    try:
        return registry.authorities(country)
    except KeyError:
        return None


def _reporting_context(reporting: dict) -> str:
    lines = [
        f"COUNTRY-SPECIFIC REPORTING CONTACTS FOR {reporting['country']}:",
        "Use these concrete contacts if the user asks how to report, escalate, "
        "or get official support. Do not imply you are filing a report for them.",
    ]
    police = reporting.get("police_cybercrime") or {}
    if police.get("name"):
        lines.append(
            f"- Police/cybercrime: {police['name']} "
            f"{police.get('phone', '')} {police.get('url', '')}".strip()
        )
    equality = reporting.get("equality_body") or {}
    if equality.get("name"):
        lines.append(
            f"- Equality body: {equality['name']} {equality.get('url', '')}".strip()
        )
    for hotline in reporting.get("hotlines", []):
        lines.append(
            f"- Hotline: {hotline.get('name', '')} "
            f"{hotline.get('phone', '')} {hotline.get('url', '')}".strip()
        )
    for helpline in reporting.get("helplines", []):
        lines.append(
            f"- Helpline: {helpline.get('name', '')} "
            f"{helpline.get('phone', '')} {helpline.get('audience', '')}".strip()
        )
    for url in reporting.get("report_urls", []):
        lines.append(f"- Report URL: {url}")
    return "\n".join(lines)


def _retrieval_references(citations: list[dict]) -> list[dict]:
    return [
        {
            "id": f"S{index}",
            "title": citation.get("source", "Source"),
            "url": citation.get("url", ""),
            "file": citation.get("file", ""),
            "locator": (
                f"p.{citation['page']}"
                if citation.get("page") not in (None, "")
                else ""
            ),
            "excerpt": citation.get("text", ""),
        }
        for index, citation in enumerate(citations, start=1)
    ]


def _analysis_references(analysis: dict | None) -> list[dict]:
    if not analysis:
        return []

    references = []
    for rationale in analysis.get("rationale", []):
        reference = norms.citation_reference(rationale.get("citation_id", ""))
        if reference:
            references.append({
                **reference,
                "detail": rationale.get("reason", ""),
            })

    for case in analysis.get("related_cases", []):
        references.append({
            "id": case.get("appno", ""),
            "title": case.get("name", "European Court of Human Rights case"),
            "url": case.get("url", ""),
            "file": "",
            "detail": case.get("conclusion", ""),
        })
    return references


def _reporting_references(reporting: dict | None) -> list[dict]:
    if not reporting:
        return []

    references = []
    for key in ("police_cybercrime", "equality_body"):
        contact = reporting.get(key) or {}
        if contact.get("url"):
            references.append({
                "id": key,
                "title": contact.get("name") or contact["url"],
                "url": contact["url"],
                "file": "",
                "detail": contact.get("phone", ""),
            })

    for index, hotline in enumerate(reporting.get("hotlines", []), start=1):
        if hotline.get("url"):
            references.append({
                "id": f"hotline-{index}",
                "title": hotline.get("name") or hotline["url"],
                "url": hotline["url"],
                "file": "",
                "detail": hotline.get("phone", ""),
            })

    for index, url in enumerate(reporting.get("report_urls", []), start=1):
        references.append({
            "id": f"report-url-{index}",
            "title": "Official reporting form",
            "url": url,
            "file": "",
            "detail": "",
        })
    return references


def _response_references(
    citations: list[dict],
    analysis: dict | None,
    reporting: dict | None,
) -> list[dict]:
    references = (
        _retrieval_references(citations)
        + _analysis_references(analysis)
        + _reporting_references(reporting)
    )
    unique = []
    seen = set()
    for reference in references:
        reference = {
            **reference,
            "url": source_documents.normalize_reference_url(
                reference.get("url", "")
            ),
        }
        key = (
            reference.get("url", ""),
            reference.get("file", ""),
            reference.get("id", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(reference)
    return unique


def handle(session_id: str, role: str, age_band: str, country: str,
           message: str, attachment: str | None = None, mode: str | None = None) -> dict:
    sess = _session(session_id)

    # 1. Deterministic quote extraction (no LLM): a quoted block in the message
    # is a pasted post. Kept before triage so the quote can be stripped from
    # the triage text.
    quoted = extract.extract_quoted(message)

    # 2. Triage screen: students only (see safety.triage_flag contract),
    # rule-based, runs before any LLM call, and cannot fail at demo time.
    #
    # Only the student's own words are screened, never pasted content. Triage
    # patterns such as "about me" inside a quoted post are the harasser's
    # words, not a first-person distress signal from the student, so the quoted
    # segment is stripped before screening. (Explicit attachments were never
    # screened; this preserves that property for inline quotes.)
    triage_text = message.replace(quoted[1], "") if quoted else message
    if role == "student" and sess["state"] != "triage" and safety.triage_flag(triage_text):
        sess["state"] = "triage"
        reply = personas.triage_response(country, age_band)
        sess["history"] += [{"role": "user", "content": message},
                            {"role": "assistant", "content": reply}]
        return {"reply": reply, "analysis": None, "citations": [],
                "references": [], "reporting": None, "summary": None,
                "triage": True}

    system = personas.system_prompt(role=role, age_band=age_band, country=country)
    # A student who already pivoted through triage gets a gentle standing note on
    # every later turn, so the assistant stays in support mode without re-triggering.
    if sess["state"] == "triage":
        system += _TARGETED_NOTE

    context_parts, analysis_out, citations, reporting = [], None, [], None

    # 3. Resolve the post to analyse: explicit attachment wins, then the quoted
    # block, then one small LLM extraction with a verbatim-substring guard.
    post = attachment or (quoted[0] if quoted else None) or extract.llm_extract(message)

    # 4. A resolved post -> structured analysis as context. classify.analyze
    # already age-gates severe-tier example spans via safety.gate_spans, so no
    # extra under-13 handling is needed here.
    if post:
        result = classify.analyze(post, country=country,
                                  age_band=age_band, role=role)
        analysis_out = result.model_dump()
        # Awareness dashboard: categorical signals only, never content.
        stats.record(tier=result.tier, barriers=[b.id for b in result.barriers],
                     themes=result.themes, country=country, role=role,
                     age_band=age_band)
        if result.tier >= 3:
            stored_reporting = _country_reporting(country)
            if stored_reporting:
                sess["last_reporting"] = stored_reporting
        context_parts.append(
            "STRUCTURED ANALYSIS OF THE POST THE USER SHARED (ground your "
            "answer in this; the user's screen already displays it as a card, "
            "so do not restate it):\n" + json.dumps(analysis_out))
    # 5. Otherwise ground open questions in retrieved sources.
    else:
        hits = retrieval.search(message, k=4)
        citations = hits
        if hits:
            context_parts.append("SOURCE PASSAGES:\n" + retrieval.context_block(hits))

    if not reporting and _reporting_requested(message):
        reporting = sess.get("last_reporting") or _country_reporting(country)
    if reporting and _reporting_requested(message):
        context_parts.append(_reporting_context(reporting))

    user_content = message
    if attachment:
        # Posts extracted from the message are already inside it; only an
        # explicit attachment needs appending.
        user_content += f"\n\nATTACHED POST:\n{attachment}"
    if context_parts:
        user_content += "\n\n" + "\n\n".join(context_parts)

    messages = ([{"role": "system", "content": system}]
                + sess["history"][-2 * MAX_TURNS:]
                + [{"role": "user", "content": user_content}])
    reply = safety.soften_determinations(llm.complete(messages))
    summary = (
        _generated_summary(reply, role, age_band)
        if analysis_out and role == "student"
        else None
    )

    # History stores the user's RAW message, not user_content: keeping injected
    # context (analysis dumps, source passages) out of history prevents it from
    # accumulating turn over turn and blowing the window.
    sess["history"] += [{"role": "user", "content": message},
                        {"role": "assistant", "content": reply}]
    return {
        "reply": reply,
        "summary": summary,
        "analysis": analysis_out,
        "citations": citations,
        "references": _response_references(
            citations,
            analysis_out,
            reporting,
        ),
        "reporting": reporting,
        "triage": False,
    }

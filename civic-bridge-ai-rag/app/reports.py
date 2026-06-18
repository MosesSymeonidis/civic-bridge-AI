"""Local incident store + deterministic report draft.

Submission to real authorities is intentionally NOT implemented (roadmap:
secure submission API). The draft tells the user where to send the report.
"""
import sqlite3
from datetime import datetime, timezone

from app import config, registry

DB_PATH = config.REPORTS_DB

_SCHEMA = """CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT, country TEXT, role TEXT, text TEXT,
  tier INTEGER, draft TEXT
)"""


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(_SCHEMA)
    return conn


def _draft(text, country, tier, tier_label, rationale) -> str:
    lines = [
        "INCIDENT REPORT (DRAFT, prepared with Civic Bridge AI for human review)",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        f"Country context: {country}",
        "",
        "Reported content (verbatim):",
        f'"{text}"',
        "",
        f"Preliminary risk signal: tier {tier} ({tier_label}), per the graduated",
        "severity model of Council of Europe Recommendation CM/Rec(2022)16.",
        "This is NOT a legal determination; assessment belongs to the competent",
        "authorities after human review.",
        "",
        "Grounds considered:",
    ]
    for ref in rationale:
        lines.append(f"- [{ref['citation_id']}] {ref['reason']}")
    try:
        auth = registry.authorities(country)
        lines += ["", "Where to send this report:"]
        if auth["police_cybercrime"]["name"]:
            pc = auth["police_cybercrime"]
            lines.append(f"- {pc['name']} ({pc.get('url', '')} {pc.get('phone', '')})")
        if auth["equality_body"]["name"]:
            eb = auth["equality_body"]
            lines.append(f"- {eb['name']} ({eb.get('url', '')})")
        for h in auth["hotlines"]:
            lines.append(f"- {h['name']} ({h.get('url', '')} {h.get('phone', '')})")
    except KeyError:
        pass
    lines += ["", "Prepared with human oversight and transparency safeguards in line",
              "with the CoE Framework Convention on AI (CETS 225)."]
    return "\n".join(lines)


def create_report(text, country, role, tier, tier_label, rationale) -> dict:
    draft = _draft(text, country, tier, tier_label, rationale)
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO reports (created, country, role, text, tier, draft) VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), country, role, text, tier, draft),
        )
        conn.commit()
        rid = cur.lastrowid
    finally:
        conn.close()
    return {"id": rid, "draft": draft}


def get_report(report_id: int) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id, created, country, role, text, tier, draft FROM reports WHERE id=?",
            (report_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    keys = ["id", "created", "country", "role", "text", "tier", "draft"]
    return dict(zip(keys, row))

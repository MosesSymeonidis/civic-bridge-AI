"""Privacy-preserving aggregate statistics for the awareness dashboard.

Records ONLY categorical signals per analysis: country, role, age band, tier,
barrier IDs, themes, and a timestamp. Never the analysed text, never any
identifier. Aggregates can therefore be shown publicly without enabling the
identification of a student, school, victim, witness, or small local group.

Best-effort by design: recording failures are swallowed (with a log line) so
statistics can never break a user-facing request.
"""
import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone

from app import config

logger = logging.getLogger(__name__)

DB_PATH = config.REPORTS_DB  # same demo database file, separate table

_SCHEMA = """CREATE TABLE IF NOT EXISTS analysis_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT, country TEXT, role TEXT, age_band TEXT,
  tier INTEGER, barriers TEXT, themes TEXT
)"""


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(_SCHEMA)
    return conn


def record(tier: int, barriers: list[str], themes: list[str],
           country: str | None = None, role: str | None = None,
           age_band: str | None = None) -> None:
    try:
        conn = _conn()
        try:
            conn.execute(
                "INSERT INTO analysis_events "
                "(created, country, role, age_band, tier, barriers, themes) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), country or "",
                 role or "", age_band or "", tier,
                 json.dumps(barriers), json.dumps(themes)),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("stats recording failed (ignored): %s", exc)


def aggregate() -> dict:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT created, country, role, tier, barriers, themes "
            "FROM analysis_events").fetchall()
        try:
            reports_total = conn.execute(
                "SELECT COUNT(*) FROM reports").fetchone()[0]
        except sqlite3.OperationalError:
            reports_total = 0
    finally:
        conn.close()

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    by_tier: Counter = Counter()
    barriers: Counter = Counter()
    themes: Counter = Counter()
    by_role: Counter = Counter()
    by_country: Counter = Counter()
    last_7_days = 0
    for created, country, role, tier, barriers_json, themes_json in rows:
        by_tier[tier] += 1
        for b in json.loads(barriers_json or "[]"):
            barriers[b] += 1
        for t in json.loads(themes_json or "[]"):
            themes[t] += 1
        if role:
            by_role[role] += 1
        if country:
            by_country[country] += 1
        if created >= week_ago:
            last_7_days += 1

    return {
        "analyses_total": len(rows),
        "analyses_last_7_days": last_7_days,
        "reports_total": reports_total,
        "by_tier": {str(t): by_tier.get(t, 0) for t in (1, 2, 3, 4)},
        "top_barriers": barriers.most_common(7),
        "top_themes": themes.most_common(8),
        "by_role": dict(by_role),
        "by_country": dict(by_country),
        "privacy_note": (
            "Aggregated categorical signals only. No analysed text, no "
            "usernames, no identifiers are stored or shown."
        ),
    }

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
KNOWLEDGE = DATA / "knowledge"
RAW = DATA / "raw"
CHROMA_PATH = str(DATA / "index" / "chroma")
REPORTS_DB = DATA / "reports.db"

MODEL_CHAIN = [
    m.strip()
    for m in os.getenv(
        "CBA_MODEL_CHAIN",
        "openai/gpt-4.1,anthropic/claude-sonnet-4-6,ollama/llama3.1",
    ).split(",")
]
VISION_MODEL_CHAIN = [
    m.strip()
    for m in os.getenv(
        "CBA_VISION_MODEL_CHAIN",
        "openai/gpt-4.1,anthropic/claude-sonnet-4-6",
    ).split(",")
]
EMBED_MODEL = os.getenv("CBA_EMBED_MODEL", "openai/text-embedding-3-small")
IMAGE_MAX_BYTES = int(os.getenv("CBA_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
IMAGE_TEXT_MAX_CHARS = int(os.getenv("CBA_IMAGE_TEXT_MAX_CHARS", "4000"))

AGE_BANDS = ["6-9", "10-13", "14-17", "18+", "mixed"]
ROLES = ["student", "teacher"]

"""Database helpers for the v2 assertion layer."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V1_DB_PATH = PROJECT_ROOT / "euro_sdt.db"
V2_DB_PATH = PROJECT_ROOT / "euro_sdt_v2.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
AUDIT_DIR = PROJECT_ROOT / "audit"
GRAPH_DIR = PROJECT_ROOT / "graph"
WIKI_V2_DIR = PROJECT_ROOT / "wiki_v2"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def uid(prefix: str = "") -> str:
    value = uuid.uuid4().hex
    return f"{prefix}{value}" if prefix else value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(text: str) -> str:
    """One slug function for the whole pipeline."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_name(text: str) -> str:
    """Normalise a display name for entity resolution (not for IDs)."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2019']", "", text)
    text = re.sub(r"\b(hon|sir|dame|dr|prof|mr|mrs|ms)\b\.?", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def org_merge_key(name: str) -> str:
    """Stable key for merging organisation name variants.

    Parenthetical qualifiers are removed, so "European People's Party (EPP)"
    and "European People's Party" share a key. Sub-entities with additional
    words (e.g. "… (EPP) group") keep a different key.
    """
    text = re.sub(r"\([^)]*\)", " ", str(name))
    text = re.sub(r"[\u2013\u2014]", "-", text)
    return normalize_name(text)


def connect(path: Path | str = V2_DB_PATH) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db


def init_db(path: Path | str = V2_DB_PATH) -> sqlite3.Connection:
    db = connect(path)
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    db.commit()
    return db


def reset_db(path: Path | str = V2_DB_PATH) -> sqlite3.Connection:
    p = Path(path)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(p) + suffix)
        if candidate.exists():
            candidate.unlink()
    return init_db(p)


def table_counts(db: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "source_document",
        "sentence",
        "entity",
        "entity_alias",
        "claim",
        "evidence",
        "assertion",
        "rejection",
        "organisation_profile",
        "adjudication",
        "review",
    ]
    out = {}
    for table in tables:
        out[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return out

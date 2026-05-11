"""Database utilities — connection, entity cache, common queries."""

import sqlite3, re
from .config import DB_PATH


def connect(readonly: bool = False) -> sqlite3.Connection:
    """Return a connection to the project database."""
    uri = f"file:{DB_PATH}{'?mode=ro' if readonly else ''}"
    db = sqlite3.connect(uri if readonly else DB_PATH, uri=readonly)
    if not readonly:
        db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlite3.Row
    return db


def slugify(text: str) -> str:
    """Convert arbitrary text to a URL-safe slug."""
    # Normalise unicode
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def get_or_create_entity(db: sqlite3.Connection, name: str, etype: str = "organisation",
                         category: str | None = None) -> str:
    """Look up an entity by name (case-insensitive) or create it. Returns slug/id."""
    key = name.lower().strip()
    slug = slugify(name)
    row = db.execute("SELECT id FROM entity WHERE LOWER(name)=?", [key]).fetchone()
    if row:
        return row[0]
    row = db.execute("SELECT id FROM entity WHERE id=?", [slug]).fetchone()
    if row:
        return row[0]
    cat = category or etype
    try:
        db.execute(
            "INSERT OR IGNORE INTO entity (id, name, type, category) VALUES (?,?,?,?)",
            [slug, name, etype, cat],
        )
    except Exception:
        row = db.execute("SELECT id FROM entity WHERE LOWER(name)=?", [key]).fetchone()
        if row:
            return row[0]
        return slug
    return slug

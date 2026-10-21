"""Build the v2 source corpus and sentence table.

Every source document is snapshotted by SHA-256 and split once by the v2
tokeniser. Sentence IDs are the only citation locator used downstream.
"""

from __future__ import annotations

import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .db import PROJECT_ROOT, normalize_name, now, sha256_text, slugify
from .entities import entity_id_for
from .tokenizer import sentence_spans

SOURCES_DIR = PROJECT_ROOT / "sources"
KINDS = {
    "wikipedia": ("wikipedia", "CC BY-SA 4.0"),
    "dg_cvs": ("dg_cv", "European Commission public document"),
    "declarations": ("declaration", "European Commission public document"),
    "cjeu": ("cjeu", "CJEU public document"),
    "revolving_door": ("revolving_door", "European Commission public document"),
    "org_sites": ("org_site", "Organisation public web page"),
    "entities_md": ("entity_md", "Project research note"),
}


def _manifest_index() -> dict[str, dict]:
    path = SOURCES_DIR / "manifest.json"
    if not path.exists():
        return {}
    entries = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for entry in entries:
        out[f"{entry.get('subdir')}/{entry.get('doc_id')}"] = entry
    return out


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _doc_title(stem: str, kind: str) -> str:
    clean = re.sub(r"^(doi-|cit-|wiki-)", "", stem)
    clean = re.sub(r"-(en|fr|de)$", "", clean)
    return clean.replace("-", " ").strip().title()


def _find_person_id(db: sqlite3.Connection, *candidates: str) -> str | None:
    for candidate in candidates:
        if not candidate:
            continue
        found = entity_id_for(db, candidate, "person")
        if found:
            return found
        found = entity_id_for(db, candidate.replace("-", " "), "person")
        if found:
            return found
        found = entity_id_for(db, re.sub(r"^(doi-|mep-|cit-)", "", candidate), "person")
        if found:
            return found
    return None


def build_corpus(db: sqlite3.Connection, fetch_missing: bool = False) -> dict[str, str]:
    """Populate source_document and sentence. Returns doc stem -> doc id."""
    manifest = _manifest_index()
    doc_by_stem: dict[str, str] = {}
    inserted = 0

    for subdir, (kind, license_name) in KINDS.items():
        directory = SOURCES_DIR / subdir
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.txt")):
            stem = path.stem
            doc_id = f"{kind}-{stem}"
            text = _read_text(path)
            if not text.strip():
                continue
            meta = manifest.get(f"{subdir}/{stem}", {})
            title = _doc_title(stem, kind)
            subject = None
            if kind == "wikipedia":
                # A Wikipedia page may describe a person, a commission, or an organisation.
                subject = _find_person_id(db, stem, title)
            else:
                subject = _find_person_id(
                    db,
                    stem,
                    re.sub(r"^doi-", "", stem),
                    re.sub(r"^doi-(.*)-en$", r"\1", stem),
                    title,
                )
            url = None
            if kind == "wikipedia":
                url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            stat = path.stat()
            retrieved = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
            existing = db.execute("SELECT id FROM source_document WHERE id=?", (doc_id,)).fetchone()
            if existing:
                db.execute("DELETE FROM sentence WHERE doc_id=?", (doc_id,))
                db.execute("DELETE FROM source_document WHERE id=?", (doc_id,))
            db.execute(
                "INSERT INTO source_document (id, kind, title, url, local_path, text_sha256, char_count, "
                "sentence_count, retrieved_at, revision_id, access_date, license, subject_id, metadata_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    doc_id,
                    kind,
                    title,
                    url,
                    str(path.relative_to(PROJECT_ROOT)),
                    sha256_text(text),
                    len(text),
                    0,
                    retrieved,
                    meta.get("revision_id"),
                    retrieved[:10],
                    license_name,
                    subject,
                    json.dumps({"manifest": meta, "subdir": subdir}, ensure_ascii=False),
                ),
            )
            spans = sentence_spans(text)
            rows = [
                (
                    f"{doc_id}:{span.ordinal}",
                    doc_id,
                    span.ordinal,
                    span.char_start,
                    span.char_end,
                    span.text,
                    sha256_text(span.text),
                )
                for span in spans
            ]
            db.executemany(
                "INSERT INTO sentence (id, doc_id, ordinal, char_start, char_end, text, text_sha256) "
                "VALUES (?,?,?,?,?,?,?)",
                rows,
            )
            db.execute("UPDATE source_document SET sentence_count=? WHERE id=?", (len(rows), doc_id))
            doc_by_stem[stem] = doc_id
            doc_by_stem[f"{kind}-{stem}"] = doc_id
            inserted += 1

    db.commit()
    if fetch_missing:
        fetch_missing_wikipedia(db, doc_by_stem)
    return doc_by_stem


def _wikipedia_extract(title: str) -> tuple[str | None, str | None, str | None]:
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|revisions",
        "explaintext": "1",
        "exsectionformat": "plain",
        "rvprop": "ids|timestamp",
        "redirects": "1",
        "titles": title,
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "euro-sdt/0.2 (research corpus)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None, None, None
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            return None, None, None
        text = page.get("extract") or ""
        revisions = page.get("revisions") or [{}]
        revision = revisions[0]
        return text, str(revision.get("revid") or ""), revision.get("timestamp")
    return None, None, None


def fetch_missing_wikipedia(db: sqlite3.Connection, doc_by_stem: dict[str, str],
                            cites: list[tuple[str, str, str]] | None = None) -> int:
    """Fetch Wikipedia pages cited by v1 but absent from sources/wikipedia."""
    if cites is None:
        return 0
    fetched = 0
    for cid, url, name in cites:
        if not url or "wikipedia.org/wiki/" not in url:
            continue
        title = urllib.parse.unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")
        stem = slugify(title)
        if stem in doc_by_stem:
            continue
        text, revision, timestamp = _wikipedia_extract(title)
        if not text or len(text) < 200:
            continue
        path = SOURCES_DIR / "wikipedia" / f"{stem}.txt"
        path.write_text(text, encoding="utf-8")
        doc_id = f"wikipedia-{stem}"
        subject = _find_person_id(db, stem, title)
        db.execute(
            "INSERT OR REPLACE INTO source_document (id, kind, title, url, local_path, text_sha256, "
            "char_count, sentence_count, retrieved_at, revision_id, access_date, license, subject_id, metadata_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                doc_id, "wikipedia", title, url, str(path.relative_to(PROJECT_ROOT)), sha256_text(text),
                len(text), 0, now(), revision, now()[:10], "CC BY-SA 4.0", subject,
                json.dumps({"fetched": True, "revision_timestamp": timestamp}, ensure_ascii=False),
            ),
        )
        spans = sentence_spans(text)
        db.executemany(
            "INSERT INTO sentence (id, doc_id, ordinal, char_start, char_end, text, text_sha256) "
            "VALUES (?,?,?,?,?,?,?)",
            [
                (f"{doc_id}:{s.ordinal}", doc_id, s.ordinal, s.char_start, s.char_end, s.text, sha256_text(s.text))
                for s in spans
            ],
        )
        db.execute("UPDATE source_document SET sentence_count=? WHERE id=?", (len(spans), doc_id))
        doc_by_stem[stem] = doc_id
        doc_by_stem[doc_id] = doc_id
        fetched += 1
    db.commit()
    return fetched

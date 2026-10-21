"""Resolve v1 citation rows to v2 source documents."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
import urllib.parse

from .db import AUDIT_DIR, slugify


def _candidates(cid: str, url: str | None, source_name: str) -> list[str]:
    out: list[str] = []
    if url and "wikipedia.org/wiki/" in url:
        title = urllib.parse.unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")
        out.append(slugify(title))
    for prefix in ("cit-wiki-mep-mep-", "cit-wiki-mep-", "cit-wiki-corp-", "cit-wiki-"):
        if cid.startswith(prefix):
            out.append(slugify(cid[len(prefix):]))
    if source_name:
        out.append(slugify(re.sub(r"^Wikipedia (article|page):\s*", "", source_name)))
    return [c for c in out if c]


def build_citation_map(db: sqlite3.Connection, v1: sqlite3.Connection,
                       doc_by_stem: dict[str, str]) -> dict[str, str]:
    stems = sorted({key for key in doc_by_stem if not key.startswith(("wikipedia-", "dg_cv-", "declaration-", "cjeu-", "revolving_door-", "org_site-", "entity_md-"))})
    mapping: dict[str, str] = {}
    unresolved: list[dict] = []
    for row in v1.execute("SELECT id, source_name, source_type, url FROM citation"):
        cid = row["id"]
        found = None
        for candidate in _candidates(cid, row["url"], row["source_name"]):
            if candidate in doc_by_stem:
                found = doc_by_stem[candidate]
                break
        if not found:
            for candidate in _candidates(cid, row["url"], row["source_name"]):
                match = difflib.get_close_matches(candidate, stems, n=1, cutoff=0.9)
                if match:
                    found = doc_by_stem[match[0]]
                    break
        if found:
            mapping[cid] = found
        else:
            unresolved.append({
                "citation_id": cid,
                "source_name": row["source_name"],
                "source_type": row["source_type"],
                "url": row["url"],
            })
    AUDIT_DIR.mkdir(exist_ok=True)
    (AUDIT_DIR / "citation_map.json").write_text(
        json.dumps({"resolved": mapping, "unresolved": unresolved}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return mapping

#!/usr/bin/env python3
"""Acquire Wikipedia biographies for people with no local education source."""
from __future__ import annotations

import csv
import difflib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from euro_sdt.v2.corpus import _wikipedia_extract
from euro_sdt.v2.db import AUDIT_DIR, PROJECT_ROOT, connect, now, sha256_text
from euro_sdt.v2.tokenizer import sentence_spans

GAPS = AUDIT_DIR / "education_gaps.csv"
SOURCES = PROJECT_ROOT / "sources" / "wikipedia"
API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "euro-sdt/0.2 (education research; gavin@scidonia.ai)"}


def _request(url: str) -> dict:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as exc:
            if "429" in str(exc):
                time.sleep(10 * (attempt + 1))
                continue
            return {}
    return {}


def batch_extract(titles: list[str]) -> dict[str, tuple[str, str, str]]:
    params = {
        "action": "query", "format": "json", "prop": "extracts|revisions",
        "explaintext": "1", "exsectionformat": "plain", "rvprop": "ids|timestamp",
        "redirects": "1", "titles": "|".join(titles),
    }
    data = _request(API + "?" + urllib.parse.urlencode(params))
    out = {}
    for page in data.get("query", {}).get("pages", {}).values():
        if "missing" in page:
            continue
        text = page.get("extract") or ""
        revisions = page.get("revisions") or [{}]
        out[page.get("title", "")] = (text, str(revisions[0].get("revid") or ""), revisions[0].get("timestamp") or "")
    return out


def search(name: str) -> list[str]:
    params = {
        "action": "query", "format": "json", "list": "search",
        "srsearch": f'"{name}"', "srlimit": "5",
    }
    data = _request(API + "?" + urllib.parse.urlencode(params))
    return [item["title"] for item in data.get("query", {}).get("search", [])]


def score(title: str, name: str) -> float:
    a = title.lower().replace("–", "-")
    b = name.lower().replace("–", "-")
    return difflib.SequenceMatcher(None, a, b).ratio()


def save(db, person_id: str, title: str, text: str, revision: str, timestamp: str, url: str) -> bool:
    if not text or len(text) < 200:
        return False
    SOURCES.mkdir(parents=True, exist_ok=True)
    path = SOURCES / f"edu-{person_id}.txt"
    path.write_text(text, encoding="utf-8")
    doc_id = f"wikipedia-edu-{person_id}"
    db.execute("DELETE FROM sentence WHERE doc_id=?", (doc_id,))
    db.execute("DELETE FROM source_document WHERE id=?", (doc_id,))
    db.execute(
        "INSERT INTO source_document (id, kind, title, url, local_path, text_sha256, char_count, "
        "sentence_count, retrieved_at, revision_id, access_date, license, subject_id, metadata_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, "wikipedia", title, url, str(path.relative_to(PROJECT_ROOT)), sha256_text(text),
         len(text), 0, now(), revision, now()[:10], "CC BY-SA 4.0", person_id,
         json.dumps({"search": True, "revision_timestamp": timestamp}, ensure_ascii=False)),
    )
    spans = sentence_spans(text)
    db.executemany(
        "INSERT INTO sentence (id, doc_id, ordinal, char_start, char_end, text, text_sha256) VALUES (?,?,?,?,?,?,?)",
        [(f"{doc_id}:{s.ordinal}", doc_id, s.ordinal, s.char_start, s.char_end, s.text, sha256_text(s.text)) for s in spans],
    )
    db.execute("UPDATE source_document SET sentence_count=? WHERE id=?", (len(spans), doc_id))
    return True


def main() -> int:
    db = connect()
    rows = list(csv.DictReader(GAPS.open(encoding="utf-8")))
    targets = [row for row in rows if row["local_docs"] == "0"]
    print(f"people with no local document: {len(targets)}")
    fetched = 0
    failed = []
    by_name = {row["name"]: row for row in targets}
    names = list(by_name)
    # Exact-title batches first.
    for start in range(0, len(names), 10):
        batch = names[start:start + 10]
        pages = batch_extract(batch)
        for name in batch:
            row = by_name[name]
            match = pages.get(name)
            if not match:
                # Try a case-insensitive title match.
                for title, value in pages.items():
                    if title.lower() == name.lower():
                        match = value
                        break
            if match:
                text, revision, timestamp = match
                title = name
                url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                if save(db, row["person_id"], title, text, revision, timestamp, url):
                    fetched += 1
                else:
                    failed.append(row)
            else:
                failed.append(row)
        db.commit()
        print(f"  exact batch {start + len(batch)}/{len(names)} fetched={fetched}", flush=True)
        time.sleep(2)

    # Search fallback for exact-title misses.
    searched = []
    for row in failed:
        if row["name"] not in by_name:
            continue
        titles = search(row["name"])
        titles.sort(key=lambda t: score(t, row["name"]), reverse=True)
        title = titles[0] if titles else ""
        if title and score(title, row["name"]) >= 0.55:
            text, revision, timestamp = _wikipedia_extract(title)
            if text:
                url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                if save(db, row["person_id"], title, text, revision or "", timestamp or "", url):
                    fetched += 1
                    continue
        searched.append(row)
        time.sleep(1.5)
    failed = searched
    db.commit()
    with (AUDIT_DIR / "external_sources_needed.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(failed)
    print(f"fetched {fetched}; still without source {len(failed)}")
    print("wrote audit/external_sources_needed.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

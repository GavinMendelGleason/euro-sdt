#!/usr/bin/env python3
"""Import CURIA member biographies as per-person official source documents."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from euro_sdt.v2.db import PROJECT_ROOT, connect, now, sha256_text
from euro_sdt.v2.entities import entity_id_for
from euro_sdt.v2.tokenizer import sentence_spans

URLS = {
    "court-of-justice": "https://curia.europa.eu/site/jcms/d2_5096/en/court-of-justice",
    "general-court": "https://curia.europa.eu/site/jcms/d2_5098/en/general-court",
}
OUT = PROJECT_ROOT / "sources" / "official"


def sections(soup):
    for h3 in soup.find_all("h3"):
        name = h3.get_text(" ", strip=True)
        if not name or name.lower() in ("the members",):
            continue
        parts = [name]
        for el in h3.find_all_next():
            if el.name == "h3":
                break
            if el.name in ("p", "li"):
                text = el.get_text(" ", strip=True)
                if text and text not in parts:
                    parts.append(text)
        yield name, "\n".join(parts)


def main() -> int:
    db = connect()
    OUT.mkdir(parents=True, exist_ok=True)
    saved = 0
    for court, url in URLS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "euro-sdt/0.2 (research)"})
            html = urllib.request.urlopen(req, timeout=60).read()
        except Exception as exc:
            print(f"{court}: fetch failed: {exc}")
            continue
        soup = BeautifulSoup(html, "lxml")
        for name, text in sections(soup):
            person_id = entity_id_for(db, name, "person")
            if not person_id:
                continue
            if len(text) < 200:
                continue
            path = OUT / f"cjeu-{person_id}.txt"
            path.write_text(text, encoding="utf-8")
            doc_id = f"official-cjeu-{person_id}"
            db.execute("DELETE FROM sentence WHERE doc_id=?", (doc_id,))
            db.execute("DELETE FROM source_document WHERE id=?", (doc_id,))
            db.execute(
                "INSERT INTO source_document (id, kind, title, url, local_path, text_sha256, char_count, "
                "sentence_count, retrieved_at, revision_id, access_date, license, subject_id, metadata_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, "official", f"CURIA biography: {name}", url,
                 str(path.relative_to(PROJECT_ROOT)), sha256_text(text), len(text), 0,
                 now(), None, now()[:10], "CURIA public document", person_id,
                 json.dumps({"court": court}, ensure_ascii=False)),
            )
            spans = sentence_spans(text)
            db.executemany(
                "INSERT INTO sentence (id, doc_id, ordinal, char_start, char_end, text, text_sha256) VALUES (?,?,?,?,?,?,?)",
                [(f"{doc_id}:{s.ordinal}", doc_id, s.ordinal, s.char_start, s.char_end, s.text, sha256_text(s.text)) for s in spans],
            )
            db.execute("UPDATE source_document SET sentence_count=? WHERE id=?", (len(spans), doc_id))
            saved += 1
            print(f"  {name} -> {person_id}")
    db.commit()
    print(f"saved {saved} CURIA documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

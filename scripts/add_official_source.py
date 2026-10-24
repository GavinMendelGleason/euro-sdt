#!/usr/bin/env python3
"""Fetch one official URL and attach it to a person as a source document."""
from __future__ import annotations

import argparse
import io
import json
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from euro_sdt.v2.db import PROJECT_ROOT, connect, now, sha256_text
from euro_sdt.v2.tokenizer import sentence_spans

OUT = PROJECT_ROOT / "sources" / "official"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "euro-sdt/0.2 (research)"})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    soup = BeautifulSoup(data, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--person-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", default=None)
    parser.add_argument("--text-file", default=None)
    args = parser.parse_args()
    text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else fetch_text(args.url)
    if len(text.strip()) < 100:
        print(f"too little text: {len(text)}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.person_id}.txt"
    path.write_text(text, encoding="utf-8")
    db = connect()
    doc_id = f"official-{args.person_id}"
    db.execute("DELETE FROM sentence WHERE doc_id=?", (doc_id,))
    db.execute("DELETE FROM source_document WHERE id=?", (doc_id,))
    db.execute(
        "INSERT INTO source_document (id, kind, title, url, local_path, text_sha256, char_count, "
        "sentence_count, retrieved_at, revision_id, access_date, license, subject_id, metadata_json) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, "official", args.title or args.person_id, args.url,
         str(path.relative_to(PROJECT_ROOT)), sha256_text(text), len(text), 0,
         now(), None, now()[:10], "Official public document", args.person_id,
         json.dumps({"url": args.url}, ensure_ascii=False)),
    )
    spans = sentence_spans(text)
    db.executemany(
        "INSERT INTO sentence (id, doc_id, ordinal, char_start, char_end, text, text_sha256) VALUES (?,?,?,?,?,?,?)",
        [(f"{doc_id}:{s.ordinal}", doc_id, s.ordinal, s.char_start, s.char_end, s.text, sha256_text(s.text)) for s in spans],
    )
    db.execute("UPDATE source_document SET sentence_count=? WHERE id=?", (len(spans), doc_id))
    db.commit()
    print(f"saved {doc_id}: {len(text)} chars, {len(spans)} sentences")
    print(text[:400].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

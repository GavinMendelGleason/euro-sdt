"""Full-document affiliation extraction for v2.

Unlike v1, this never truncates a biography. Each chunk is a contiguous span of
sentences, and every extracted row must name an exact evidence sentence. The
result is a claim, not an assertion: it still has to pass the locator and the
verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .claims import DocCache, _add_evidence, _insert_claim, _finish_assertions, normalize_role, predicate_for_role
from .db import AUDIT_DIR, PROJECT_ROOT, connect, now, sha256_text, uid
from .entities import aliases_for, resolve_or_create

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = os.environ.get("EURO_SDT_V2_MODEL", "deepseek-chat")
WORKERS = int(os.environ.get("EURO_SDT_V2_WORKERS", "4"))
CACHE_PATH = AUDIT_DIR / "llm_extraction_cache.json"

RELATIONS = {
    "member", "board_member", "advisory_board", "chair", "employed_by",
    "founder", "fellow", "party_member", "attendee", "affiliated_with",
}


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    AUDIT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _chunks(db: sqlite3.Connection, doc_id: str, max_sentences: int = 40, max_chars: int = 12000):
    rows = db.execute(
        "SELECT id, ordinal, text FROM sentence WHERE doc_id=? ORDER BY ordinal", (doc_id,)
    ).fetchall()
    chunk: list[sqlite3.Row] = []
    size = 0
    for row in rows:
        if chunk and (len(chunk) >= max_sentences or size + len(row["text"]) > max_chars):
            yield chunk
            chunk = chunk[-2:] if len(chunk) >= 2 else []
            size = sum(len(item["text"]) for item in chunk)
        chunk.append(row)
        size += len(row["text"])
    if chunk:
        yield chunk


def _prompt(person: str, chunk: list[sqlite3.Row]) -> str:
    numbered = "\n".join(f"[{row['ordinal']}] {row['text']}" for row in chunk)
    return f"""Extract every organisation with which {person} has a formal, documented relationship in the numbered sentences below.

INCLUDE: membership, board/trustee, supervisory board, advisory board, chair/president, executive employment (CEO, director, manager), founder, fellow, political party membership, formal affiliation.
EXCLUDE: universities, schools, and educational institutions; organisations merely mentioned in passing; organisations where {person} is not a participant; awards and honours; generic role titles.

For each relationship, return:
- "organisation": the organisation name exactly as written
- "role": the role phrase exactly as written (e.g. "Member of the Board of Trustees")
- "relation": one of member, board_member, advisory_board, chair, employed_by, founder, fellow, party_member, attendee, affiliated_with
- "evidence": the exact sentence from the numbered text that states the relationship (copy it verbatim)
- "sentence": the sentence number in brackets

RULES:
- The evidence must be copied verbatim from the text, not paraphrased.
- Do not infer membership from a person's presence in a list of names unless the list is explicitly a membership list.
- Attendance at a conference is "attendee", not "member".
- If no relationship is stated, return [].

NUMBERED SENTENCES:
{numbered}

Respond with a JSON array only: [{{"organisation":"...","role":"...","relation":"...","evidence":"...","sentence":N}}]"""


def _call(prompt: str) -> list[dict]:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        return []
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2500,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    last_error = None
    for attempt in range(1):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].replace("<|endoftext|>", "").strip()
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    parsed = parsed.get("organisations") or parsed.get("results") or []
            return parsed if isinstance(parsed, list) else []
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"extraction call failed: {last_error}")


def _apply(db: sqlite3.Connection, docs: DocCache, subject_id: str, doc_id: str,
           results: list[dict], run_id: str) -> int:
    subject_aliases = aliases_for(db, subject_id)
    added = 0
    for item in results:
        if not isinstance(item, dict):
            continue
        org = (item.get("organisation") or "").strip()
        evidence = (item.get("evidence") or "").strip()
        if not org or not evidence or len(org) < 2:
            continue
        relation = (item.get("relation") or "").strip().lower()
        role_raw = (item.get("role") or "").strip() or relation
        role = relation if relation in RELATIONS else normalize_role(role_raw)
        if role == "party_member":
            predicate = "member"
        else:
            predicate = predicate_for_role(role)
        object_id = resolve_or_create(db, org, "organisation")
        claim_id = _insert_claim(
            db, subject_id, predicate, object_id, None, role, role_raw,
            None, None, f"v2_llm:{doc_id}", "v2_llm", run_id,
        )
        _add_evidence(
            db, claim_id, doc_id, evidence, None, docs,
            subject_aliases, aliases_for(db, object_id), predicate, role,
            subject_id, subject_id,
        )
        added += 1
    return added


def extract(db: sqlite3.Connection, categories: tuple[str, ...] = ("commissioner",),
            limit: int | None = None, workers: int = WORKERS) -> dict:
    placeholders = ",".join("?" for _ in categories)
    people = db.execute(
        f"SELECT e.id, e.name FROM entity e WHERE e.kind='person' AND e.category IN ({placeholders}) "
        "AND e.status='active' ORDER BY e.name", categories
    ).fetchall()
    if limit:
        people = people[:limit]
    run_id = uid("run-")
    db.execute(
        "INSERT INTO run (id, kind, started_at, model, params_json) VALUES (?,?,?,?,?)",
        (run_id, "extraction", now(), MODEL, json.dumps({"categories": categories, "limit": limit})),
    )
    db.commit()

    docs = DocCache(db)
    cache = _load_cache()
    tasks = {}
    total_docs = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for person in people:
            doc = db.execute(
                "SELECT id FROM source_document WHERE kind='wikipedia' AND subject_id=? "
                "ORDER BY char_count DESC LIMIT 1", (person["id"],)
            ).fetchone()
            if not doc:
                continue
            total_docs += 1
            for chunk in _chunks(db, doc["id"]):
                prompt = _prompt(person["name"], chunk)
                key = sha256_text(prompt)
                if key in cache:
                    continue
                tasks[pool.submit(_call, prompt)] = (person["id"], doc["id"], key)
        results = {}
        errors = 0
        for future in as_completed(tasks):
            person_id, doc_id, key = tasks[future]
            try:
                parsed = future.result()
            except Exception:
                errors += 1
                continue
            cache[key] = parsed
            results.setdefault((person_id, doc_id), []).extend(parsed)
            if len(cache) % 20 == 0:
                _save_cache(cache)
    _save_cache(cache)

    # Cached chunks are applied too, so a rerun is idempotent.
    for person in people:
        doc = db.execute(
            "SELECT id FROM source_document WHERE kind='wikipedia' AND subject_id=? "
            "ORDER BY char_count DESC LIMIT 1", (person["id"],)
        ).fetchone()
        if not doc:
            continue
        collected = []
        for chunk in _chunks(db, doc["id"]):
            prompt = _prompt(person["name"], chunk)
            collected.extend(cache.get(sha256_text(prompt), []))
        _apply(db, docs, person["id"], doc["id"], collected, run_id)

    db.execute("UPDATE run SET finished_at=? WHERE id=?", (now(), run_id))
    db.execute("DELETE FROM rejection WHERE stage='locator'")
    db.commit()
    _finish_assertions(db, preserve_adjudicated=True)
    return {"run_id": run_id, "documents": total_docs, "llm_calls": len(tasks), "errors": errors}


def _finish_assertions(db, preserve_adjudicated=True):
    from .claims import _finish_assertions as finish
    return finish(db, preserve_adjudicated=preserve_adjudicated)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--categories", default="commissioner")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    db = connect()
    print(extract(db, tuple(args.categories.split(",")), limit=args.limit, workers=args.workers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

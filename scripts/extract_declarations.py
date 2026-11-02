#!/usr/bin/env python3
"""Extract dated affiliations from commissioners' declarations of interests.

Writes standard claims (member/board_member/advisory_board/chair/employed_by/
founder/fellow/affiliated_with) with start/end dates where the declaration
states them. Evidence is always the exact declaration sentence.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.claims import DocCache, _add_evidence, _finish_assertions, _insert_claim
from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, now, sha256_text, uid
from euro_sdt.v2.entities import aliases_for, resolve_or_create
from euro_sdt.v2.extract import _call, _chunks

CACHE_PATH = AUDIT_DIR / "llm_declaration_cache.json"
MODEL = "deepseek-chat"
RELATIONS = {"member", "board_member", "advisory_board", "chair", "employed_by", "founder", "fellow", "affiliated_with"}


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    AUDIT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def prompt(person: str, chunk: list[sqlite3.Row]) -> str:
    numbered = "\n".join(f"[{row['ordinal']}] {row['text']}" for row in chunk)
    return f"""Extract {person}'s formal organisational affiliations from this declaration of interests.

INCLUDE: memberships, board/trustee roles, advisory board roles, chair/president roles, employment, founder roles, fellowships, and honorary positions.
EXCLUDE: financial interests, shares, property, loans, family members' interests, and organisations merely mentioned without a role.
Do not infer. Only return a relationship explicitly stated in the text.

For each relationship return:
- "organisation": organisation name exactly as written
- "role": role phrase exactly as written
- "relation": one of member, board_member, advisory_board, chair, employed_by, founder, fellow, affiliated_with
- "start_date": YYYY, YYYY-MM, or YYYY-MM-DD if stated, otherwise null
- "end_date": YYYY, YYYY-MM, or YYYY-MM-DD if stated, otherwise null
- "evidence": exact sentence from the numbered text
- "sentence": sentence number in brackets

Convert dates such as "2021-November 2024" to start_date 2021 and end_date 2024-11 where possible. Do not invent a date.
If no qualifying relationship is stated, return [].

NUMBERED SENTENCES:
{numbered}

Respond with a JSON array only: [{{"organisation":"...","role":"...","relation":"...","start_date":null,"end_date":null,"evidence":"...","sentence":N}}]"""


def clean_date(value) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() in {"null", "none", "n/a", "unknown"}:
        return None
    m = re.search(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", value)
    if not m:
        y = re.search(r"\b(\d{4})\b", value)
        return y.group(1) if y else None
    year, month, day = m.group(1), m.group(2), m.group(3)
    return "-".join(x for x in (year, month, day) if x)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db = connect(args.db)
    db.row_factory = sqlite3.Row
    docs = db.execute("""
        SELECT d.id, d.subject_id, e.name
        FROM source_document d JOIN entity e ON e.id=d.subject_id
        WHERE d.kind='declaration' AND e.category='commissioner' AND e.status='active'
        ORDER BY e.name, d.id
    """).fetchall()
    # One English declaration per person where duplicates exist.
    chosen = {}
    for d in docs:
        if d['subject_id'] not in chosen or d['id'].endswith('-en'):
            chosen[d['subject_id']] = d
    docs = list(chosen.values())[:args.limit]
    print(f"declarations: {len(docs)}")
    cache = load_cache()
    tasks = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for d in docs:
            for index, chunk in enumerate(_chunks(db, d['id'], max_sentences=40)):
                p = prompt(d['name'], chunk)
                key = f"{MODEL}|{sha256_text(p)}"
                if key not in cache:
                    tasks[pool.submit(_call, p, MODEL, False)] = (d['subject_id'], d['id'], key)
        errors = 0
        for future in as_completed(tasks):
            subject, doc_id, key = tasks[future]
            try:
                cache[key] = future.result()
            except Exception:
                errors += 1
    save_cache(cache)

    docs_cache = DocCache(db)
    run_id = uid('run-')
    db.execute("INSERT INTO run (id, kind, started_at, model, params_json) VALUES (?,?,?,?,?)",
               (run_id, 'declaration_extraction', now(), MODEL, json.dumps({'docs': len(docs)})))
    added = 0
    for d in docs:
        for index, chunk in enumerate(_chunks(db, d['id'], max_sentences=40)):
            p = prompt(d['name'], chunk)
            for item in cache.get(f"{MODEL}|{sha256_text(p)}", []):
                if not isinstance(item, dict):
                    continue
                org = (item.get('organisation') or '').strip()
                evidence = (item.get('evidence') or '').strip()
                if not org or not evidence:
                    continue
                relation = (item.get('relation') or '').strip().lower()
                if relation not in RELATIONS:
                    continue
                role_raw = (item.get('role') or '').strip() or relation
                start = clean_date(item.get('start_date'))
                end = clean_date(item.get('end_date'))
                if start and end and start > end:
                    start, end = end, start
                if args.dry_run:
                    print(d['name'], '|', org, '|', relation, '|', start, end, '|', role_raw)
                    added += 1
                    continue
                object_id = resolve_or_create(db, org, 'organisation')
                claim_id = _insert_claim(db, d['subject_id'], relation, object_id, None,
                                         relation, role_raw, start, end,
                                         f"declaration:{d['id']}", 'v2_declaration', run_id)
                # Preserve a date if an existing claim already has one.
                existing = db.execute('SELECT start_date,end_date FROM claim WHERE id=?', (claim_id,)).fetchone()
                if existing and (existing['start_date'] or existing['end_date']):
                    if not existing['start_date'] and start:
                        db.execute('UPDATE claim SET start_date=? WHERE id=?', (start, claim_id))
                    if not existing['end_date'] and end:
                        db.execute('UPDATE claim SET end_date=? WHERE id=?', (end, claim_id))
                _add_evidence(db, claim_id, d['id'], evidence,
                              item.get('sentence'), docs_cache,
                              aliases_for(db, d['subject_id']), aliases_for(db, object_id),
                              relation, relation, d['subject_id'], d['subject_id'])
                added += 1
    if not args.dry_run:
        db.commit()
        _finish_assertions(db, preserve_adjudicated=True)
    print(f"candidates/added: {added}; errors: {errors}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

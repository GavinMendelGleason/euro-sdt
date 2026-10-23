#!/usr/bin/env python3
"""Fill missing education claims from the local source corpus.

Selects active persons with no verified `educated_at` claim, reads their
Wikipedia/DG-CV/CJEU/declaration documents, and asks the model for explicit
education sentences. Every candidate is located deterministically and graded by
the same v2 evidence layer; nothing is accepted without a quote.

Examples:
  python scripts/fill_education.py --dry-run --limit 20
  python scripts/fill_education.py --db /tmp/euro_sdt_v2_edu.db --categories commissioner,dg
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.claims import DocCache, _add_evidence, _finish_assertions, _insert_claim
from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, now, sha256_text, uid
from euro_sdt.v2.entities import aliases_for, entity_id_for, resolve_or_create
from euro_sdt.v2.extract import _call, _chunks

CACHE_PATH = AUDIT_DIR / "llm_education_cache.json"
DOC_KINDS = ("wikipedia", "dg_cv", "cjeu", "declaration")
MODEL = "deepseek-chat"


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


def _prompt(person: str, chunk: list[sqlite3.Row]) -> str:
    numbered = "\n".join(f"[{row['ordinal']}] {row['text']}" for row in chunk)
    return f"""Extract every educational institution and degree for {person} from the numbered sentences.

INCLUDE only explicit statements that {person} studied at, graduated from, attended, or received a degree from an institution. Include the institution name exactly as written, the degree and field if stated, and the exact sentence.
EXCLUDE professorships, honorary degrees, lectureships, board memberships, and institutions mentioned only in passing.
Do not infer. If the text does not state the education, return [].

Return JSON only:
[{{"institution":"...","degree":"...","field":"...","evidence":"exact sentence","sentence":N}}]

NUMBERED SENTENCES:
{numbered}"""


BAD_INSTITUTIONS = ('same university', 'that same', 'universities of', 'bonn and hamburg')
BAD_EVIDENCE = (
    'chartered', 'certified', 'certificate', 'accountant', 'engineering council',
    'school leaving', 'high school', 'secondary school', 'maturit', 'abitur',
    'baccalaur', 'course', 'training', 'seminar', 'executive education',
)


def _valid_candidate(item: dict) -> bool:
    inst = (item.get('institution') or '').lower().strip()
    evidence = (item.get('evidence') or '').lower()
    if not inst or any(bad in inst for bad in BAD_INSTITUTIONS):
        return False
    if any(bad in evidence for bad in BAD_EVIDENCE):
        return False
    # Require a recognisable education institution or a named degree.
    markers = ('university', 'college', 'institute', 'school', 'academy', 'polytechnic',
               'ecole', 'école', 'universit', 'hochschule', 'faculty', 'heC', 'ena',
               'sciences po', 'bocconi', 'icade', 'cems')
    if not any(marker in inst for marker in markers):
        return False
    return True


INSTITUTION_ALIASES = {
    'free university of brussels': 'Université libre de Bruxelles (Free University of Brussels)',
    'college of europe - bruges': 'College of Europe',
    'college of bruges': 'College of Europe',
    'university college dublin, republic of ireland': 'University College Dublin (UCD)',
    'yale law school': 'Yale University',
    'trinity college': 'Trinity College Dublin',
    'the city university, london (u.k.)': 'City, University of London',
    'nova university, miami (u.s.a)': 'Nova University',
    'faculty of journalism, university of bucharest – bucharest': 'University of Bucharest',
    'warsaw university, institute of applied social science': 'University of Warsaw',
    'université paris ii': 'Université Paris II Panthéon-Assas',
    'alcalá de henares (madrid)': 'University of Alcalá',
    'ecole hec school of management': 'HEC Paris',
    'karl-franzens-universität graz': 'University of Graz',
}


def _resolve_institution(db: sqlite3.Connection, name: str) -> str:
    clean = INSTITUTION_ALIASES.get(name.lower().strip(), name)
    for kind in ('university', 'institution', 'organisation'):
        found = entity_id_for(db, clean, kind)
        if found:
            return found
    return resolve_or_create(db, clean, 'institution', category='university')


def _missing(db: sqlite3.Connection, categories: tuple[str, ...], limit: int | None):
    placeholders = ",".join("?" for _ in categories)
    rows = db.execute(f"""
        SELECT e.id, e.name, e.category
        FROM entity e
        WHERE e.kind='person' AND e.status='active' AND e.category IN ({placeholders})
          AND NOT EXISTS (
              SELECT 1 FROM claim c JOIN assertion a ON a.claim_id=c.id
              WHERE c.subject_id=e.id AND a.status='verified' AND c.predicate='educated_at'
          )
          AND EXISTS (SELECT 1 FROM source_document s WHERE s.subject_id=e.id)
        ORDER BY e.category, e.name
    """, categories).fetchall()
    return rows[:limit] if limit else rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--categories", default="commissioner,dg,ddg,mep,corporate_elite,cjeu_judge,cjeu_ag")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-chunks", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-existing", action="store_true",
                        help="Only apply candidates whose institution already exists")
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "education_fill")
    args = parser.parse_args()

    db = connect(args.db)
    categories = tuple(c.strip() for c in args.categories.split(",") if c.strip())
    people = _missing(db, categories, args.limit)
    print(f"people missing education with local documents: {len(people)}")

    cache = _load_cache()
    tasks = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for person in people:
            docs = db.execute(
                "SELECT id, title, kind FROM source_document WHERE subject_id=? AND kind IN ({})".format(
                    ",".join("?" for _ in DOC_KINDS)
                ),
                (person["id"], *DOC_KINDS),
            ).fetchall()
            for doc in docs:
                for index, chunk in enumerate(_chunks(db, doc["id"], max_sentences=40)):
                    if index >= args.max_chunks:
                        break
                    prompt = _prompt(person["name"], chunk)
                    key = f"{MODEL}|{sha256_text(prompt)}"
                    if key in cache:
                        continue
                    tasks[pool.submit(_call, prompt, MODEL, False)] = (person["id"], doc["id"], key)

        results = {}
        errors = 0
        for future in as_completed(tasks):
            person_id, doc_id, key = tasks[future]
            try:
                rows = future.result()
            except Exception:
                errors += 1
                continue
            cache[key] = rows
            results.setdefault((person_id, doc_id), []).extend(rows)
            if len(cache) % 20 == 0:
                _save_cache(cache)
    _save_cache(cache)

    docs = DocCache(db)
    candidates = []
    for person in people:
        docs_for_person = db.execute(
            "SELECT id FROM source_document WHERE subject_id=? AND kind IN ({})".format(
                ",".join("?" for _ in DOC_KINDS)
            ),
            (person["id"], *DOC_KINDS),
        ).fetchall()
        for doc in docs_for_person:
            collected = []
            for index, chunk in enumerate(_chunks(db, doc["id"], max_sentences=40)):
                if index >= args.max_chunks:
                    break
                prompt = _prompt(person["name"], chunk)
                collected.extend(cache.get(f"{MODEL}|{sha256_text(prompt)}", []))
            for item in collected:
                inst = (item.get("institution") or "").strip()
                evidence = (item.get("evidence") or "").strip()
                if not inst or not evidence:
                    continue
                candidates.append({
                    "person_id": person["id"], "person": person["name"], "category": person["category"],
                    "doc_id": doc["id"], "institution": inst,
                    "degree": item.get("degree") or "", "field": item.get("field") or "",
                    "evidence": evidence,
                })

    candidates = [item for item in candidates if _valid_candidate(item)]
    # One claim per person/institution; keep the candidate with the most explicit degree.
    unique = {}
    for item in candidates:
        key = (item["person_id"], item["institution"].lower())
        current = unique.get(key)
        if current is None or (len(item["degree"]) > len(current["degree"])):
            unique[key] = item
    candidates = list(unique.values())

    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(candidates[0].keys()) if candidates else [])
        writer.writeheader()
        writer.writerows(candidates)

    counts = Counter(item["category"] for item in candidates)
    lines = [
        "# Education Gap Fill",
        "",
        f"People scanned: {len(people)}. Candidates: {len(candidates)}. LLM errors: {errors}.",
        "",
        "| Category | Candidates |",
        "|---|---:|",
    ]
    for category, n in counts.most_common():
        lines.append(f"| {category} | {n} |")
    lines += ["", "## Candidates", ""]
    for item in candidates[:80]:
        lines.append(f"- **{item['person']}** — {item['institution']} — {item['degree']} {item['field']}")
        lines.append(f"  > {item['evidence'][:220]}")
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md ({len(candidates)} candidates)")

    if args.dry_run:
        return 0

    run_id = uid("run-")
    db.execute(
        "INSERT INTO run (id, kind, started_at, model, params_json) VALUES (?,?,?,?,?)",
        (run_id, "education", now(), MODEL, json.dumps({"categories": categories, "limit": args.limit})),
    )
    for item in candidates:
        if args.only_existing:
            object_id = None
            clean = INSTITUTION_ALIASES.get(item["institution"].lower().strip(), item["institution"])
            for kind in ("university", "institution", "organisation"):
                object_id = entity_id_for(db, clean, kind)
                if object_id:
                    break
            if not object_id:
                continue
        else:
            object_id = _resolve_institution(db, item["institution"])
        claim_id = _insert_claim(
            db, item["person_id"], "educated_at", object_id, None, None, None, None, None,
            f"v2_education:{item['doc_id']}", "v2_education", run_id,
        )
        _add_evidence(
            db, claim_id, item["doc_id"], item["evidence"], None, docs,
            aliases_for(db, item["person_id"]), aliases_for(db, object_id),
            "educated_at", None, item["person_id"], item["person_id"],
        )
    db.execute("DELETE FROM rejection WHERE stage='locator'")
    db.commit()
    _finish_assertions(db, preserve_adjudicated=True)
    print("database updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

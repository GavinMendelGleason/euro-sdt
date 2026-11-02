#!/usr/bin/env python3
"""Scan local sources for fellowship and scholarship mentions.

Read-only. Targets commissioners, DGs, deputy DGs, CJEU judges and advocates
general; MEPs are intentionally excluded. The output is a review queue, not a
set of assertions: every row preserves the source sentence and flags whether
the person is named in that sentence.
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from collections import Counter
from pathlib import Path

from euro_sdt.v2.claims import DocCache, _add_evidence, _finish_assertions, _insert_claim
from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, uid
from euro_sdt.v2.entities import aliases_for, resolve_or_create
from euro_sdt.v2.locate import alias_in_text

TARGET_CATEGORIES = ("commissioner", "dg", "ddg", "cjeu_judge", "cjeu_ag")

PROGRAMMES = {
    "Fulbright": r"\bfulbright\b",
    "Rhodes": r"\brhodes\b",
    "Marshall": r"\bmarshall\b",
    "Chevening": r"\bchevening\b",
    "Eisenhower": r"\beisenhower\b",
    "McCloy": r"\bmccloy\b",
    "Humboldt": r"\bhumboldt\b",
    "Guggenheim": r"\bguggenheim\b",
    "MacArthur": r"\bmacarthur\b",
    "Sloan": r"\bsloan\b",
    "Nieman": r"\bnieman\b",
    "Marie Curie": r"\bmarie (skłodowska[- ]?)?curie\b",
    "Erasmus": r"\berasmus\b",
    "Jean Monnet": r"\bjean monnet\b",
    "DAAD": r"\bdaad\b",
    "Henry Fellowship": r"\bhenry fellowship\b",
    "Schuman": r"\bschuman\b",
    "Weatherhead": r"\bweatherhead\b",
    "Draper Hills": r"\bdraper hills\b",
    "Stanford": r"\bstanford\b",
    "Harvard Kennedy": r"\bharvard kennedy\b",
    "Aspen": r"\baspen\b",
    "Young Leaders": r"\byoung leaders\b",
    "Bosch": r"\bbosch\b",
}

GENERIC = r"\b(fellow|fellowship|scholar|scholarship)\b"
FALSE_POSITIVE = re.compile(
    r"\b(fellow (party|member|commissioner|student|leader|citizen|physician|negotiator|"
    r"greek|reform|social|vice|meps?|human|country|national|democrat|republican|"
    r"traveller|delegate|countrym|citizen|countryman)|fellow commissioners?)\b",
    re.I,
)
EXCLUDE_SENTENCE = re.compile(r"\b(fellow party|fellow member|fellow commissioner|fellow student|fellow leader|fellow citizen|fellow physician|fellow negotiator|fellow greek|fellow reform|fellow social|fellow vice|fellow meps?|fellow human|fellow country|fellow national|fellow democrat|fellow republican|fellow traveller|fellow delegate)\b", re.I)


def _match_programme(text: str) -> str:
    hits = [name for name, pattern in PROGRAMMES.items() if re.search(pattern, text, re.I)]
    return "; ".join(hits)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "fellowship_scan")
    parser.add_argument("--write", action="store_true", help="write unique named candidates as fellow claims")
    args = parser.parse_args()
    db = connect(args.db)
    db.row_factory = sqlite3.Row

    placeholders = ",".join("?" for _ in TARGET_CATEGORIES)
    rows = db.execute(f"""
        SELECT e.id AS person_id, e.name, e.category, d.id AS doc_id, d.kind AS doc_kind, d.title, d.url,
               s.ordinal, s.text
        FROM sentence s
        JOIN source_document d ON d.id = s.doc_id
        JOIN entity e ON e.id = d.subject_id
        WHERE e.kind='person' AND e.status='active'
          AND e.category IN ({placeholders})
          AND (lower(s.text) LIKE '%fellow%'
               OR lower(s.text) LIKE '%scholar%'
               OR lower(s.text) LIKE '%scholarship%')
        ORDER BY e.category, e.name, d.id, s.ordinal
    """, TARGET_CATEGORIES).fetchall()

    alias_cache: dict[str, tuple[str, ...]] = {}
    existing: dict[tuple[str, str], int] = {}
    for row in db.execute("""
        SELECT c.subject_id, e.doc_id, COUNT(*) n
        FROM claim c JOIN assertion a ON a.claim_id=c.id AND a.status='verified'
        JOIN evidence e ON e.claim_id=c.id
        WHERE c.predicate='fellow'
        GROUP BY c.subject_id, e.doc_id
    """):
        existing[(row["subject_id"], row["doc_id"])] = row["n"]

    out_rows = []
    for row in rows:
        text = row["text"]
        if EXCLUDE_SENTENCE.search(text):
            continue
        aliases = alias_cache.setdefault(row["person_id"], aliases_for(db, row["person_id"]))
        named = bool(alias_in_text(text, aliases))
        programme = _match_programme(text)
        generic = bool(re.search(GENERIC, text, re.I))
        if not programme and not generic:
            continue
        out_rows.append({
            "category": row["category"],
            "person": row["name"],
            "person_id": row["person_id"],
            "doc_id": row["doc_id"],
            "doc_kind": row["doc_kind"],
            "doc_title": row["title"],
            "url": row["url"] or "",
            "sentence": row["ordinal"],
            "programme": programme,
            "generic_term": generic,
            "subject_named_in_sentence": named,
            "document_subject_fallback": not named,
            "existing_fellow_claims_in_doc": existing.get((row["person_id"], row["doc_id"]), 0),
            "text": text.replace("\n", " "),
        })

    # Select one clean row per person/programme for the unique list.
    unique_named = []
    seen_named = set()
    for r in out_rows:
        if not r["programme"]:
            continue
        key = (r["person"], r["programme"])
        if key in seen_named:
            continue
        alternatives = [x for x in out_rows if (x["person"], x["programme"]) == key]
        alternatives.sort(key=lambda x: (not x["subject_named_in_sentence"], x["doc_kind"] == "official"))
        unique_named.append(alternatives[0])
        seen_named.add(key)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()) if out_rows else [])
        writer.writeheader()
        writer.writerows(out_rows)

    by_cat = Counter(r["category"] for r in out_rows)
    by_prog = Counter(p for r in out_rows for p in r["programme"].split("; ") if p)
    lines = [
        "# Fellowship and scholarship scan",
        "",
        f"Target categories: {', '.join(TARGET_CATEGORIES)}. MEPs excluded.",
        f"Sentences: {len(out_rows)}.",
        "",
        "| Category | Sentences |",
        "|---|---:|",
    ]
    for cat, n in by_cat.most_common():
        lines.append(f"| {cat} | {n} |")
    lines += ["", "| Named programme | Sentences |", "|---|---:|"]
    for prog, n in by_prog.most_common():
        lines.append(f"| {prog} | {n} |")
    lines += [
        "",
        "`subject_named_in_sentence=0` marks sentences that rely on the document subject;",
        "review these first, because official CURIA sections can contain adjacent biographies.",
        "",
        "## Named-programme sentences",
        "",
    ]
    for r in out_rows:
        if r["programme"]:
            lines.append(f"- **{r['person']}** ({r['category']}) — {r['programme']} — `{r['doc_id']}:{r['sentence']}`")
            lines.append(f"  > {r['text'][:500]}")
    lines += ["", "## Unique named candidates", ""]
    for best in unique_named:
        lines.append(f"- **{best['person']}** ({best['category']}) — {best['programme']} — `{best['doc_id']}:{best['sentence']}`")
        lines.append(f"  > {best['text'][:500]}")
    lines += ["", "## Generic fellow/scholar sentences", ""]
    for r in out_rows:
        if not r["programme"]:
            lines.append(f"- **{r['person']}** ({r['category']}) — `{r['doc_id']}:{r['sentence']}`")
            lines.append(f"  > {r['text'][:500]}")
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md ({len(out_rows)} sentences)")

    if args.write:
        docs = DocCache(db)
        written = 0
        for item in unique_named:
            programme = item["programme"]
            if programme == "Marshall":
                # German Marshall Fund fellows are already represented by the general extractor.
                continue
            # Skip if a verified fellow claim for this person already names the programme.
            existing = db.execute(
                "SELECT 1 FROM claim c JOIN assertion a ON a.claim_id=c.id AND a.status='verified' "
                "LEFT JOIN entity o ON o.id=c.object_id "
                "WHERE c.subject_id=? AND c.predicate='fellow' AND lower(coalesce(o.name,'')) LIKE ?",
                (item["person_id"], f"%{programme.lower()}%"),
            ).fetchone()
            if existing:
                continue
            object_id = resolve_or_create(db, programme, "organisation", category="fellowship_programme")
            claim_id = _insert_claim(
                db, item["person_id"], "fellow", object_id, None, "fellow", programme,
                None, None, f"v2_fellowship:{item['doc_id']}", "v2_fellowship", None,
            )
            _add_evidence(
                db, claim_id, item["doc_id"], item["text"], item["sentence"], docs,
                aliases_for(db, item["person_id"]), aliases_for(db, object_id),
                "fellow", "fellow", item["person_id"], item["person_id"],
            )
            written += 1
        db.commit()
        _finish_assertions(db, preserve_adjudicated=True)
        print(f"wrote {written} fellow claims")
    print("by category:", dict(by_cat))
    print("named programmes:", dict(by_prog))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit the v2 assertion layer and enforce its invariants."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter

from collections import defaultdict

from .db import AUDIT_DIR, GRAPH_DIR, WIKI_V2_DIR, connect, normalize_name, org_merge_key, table_counts
from .entities import ORG_KINDS


def audit(db: sqlite3.Connection) -> dict:
    counts = table_counts(db)
    status = Counter()
    grade = Counter()
    for row in db.execute("SELECT status, evidence_grade, COUNT(*) FROM assertion GROUP BY 1,2"):
        status[row[0]] += row[2]
        grade[row[1]] += row[2]
    rejections = Counter()
    for row in db.execute("SELECT stage, COUNT(*) FROM rejection GROUP BY 1"):
        rejections[row[0]] = row[1]
    locators = Counter()
    for row in db.execute("SELECT locator_status, COUNT(*) FROM evidence GROUP BY 1"):
        locators[row[0]] = row[1]
    sources = Counter()
    for row in db.execute("SELECT kind, COUNT(*) FROM source_document GROUP BY 1"):
        sources[row[0]] = row[1]
    predicates = Counter()
    for row in db.execute("SELECT predicate, COUNT(*) FROM claim GROUP BY 1"):
        predicates[row[0]] = row[1]

    checks = {
        "verified_without_located_evidence": db.execute("""
            SELECT COUNT(*) FROM assertion a
            WHERE a.status='verified' AND NOT EXISTS (
                SELECT 1 FROM evidence e WHERE e.claim_id=a.claim_id AND e.locator_status='located'
            )
        """).fetchone()[0],
        "verified_grade_none": db.execute(
            "SELECT COUNT(*) FROM assertion WHERE status='verified' AND evidence_grade='none'"
        ).fetchone()[0],
        "located_evidence_without_sentence": db.execute("""
            SELECT COUNT(*) FROM evidence WHERE locator_status='located'
              AND (sentence_start_id IS NULL OR sentence_end_id IS NULL)
        """).fetchone()[0],
        "evidence_without_doc": db.execute("""
            SELECT COUNT(*) FROM evidence e LEFT JOIN source_document d ON d.id=e.doc_id WHERE d.id IS NULL
        """).fetchone()[0],
        "claims_without_object": db.execute(
            "SELECT COUNT(*) FROM claim WHERE object_id IS NULL AND object_literal IS NULL"
        ).fetchone()[0],
        "duplicate_active_entities": _duplicate_count(db),
        "quarantined_entities": db.execute(
            "SELECT COUNT(*) FROM entity WHERE status='quarantined'"
        ).fetchone()[0],
        "documents_without_sentences": db.execute("""
            SELECT COUNT(*) FROM source_document s
            WHERE NOT EXISTS (SELECT 1 FROM sentence x WHERE x.doc_id=s.id)
        """).fetchone()[0],
        "documents_without_hash": db.execute(
            "SELECT COUNT(*) FROM source_document WHERE text_sha256 IS NULL OR text_sha256=''"
        ).fetchone()[0],
        "recovered_evidence": db.execute(
            "SELECT COUNT(*) FROM evidence WHERE notes LIKE 'recovered%'"
        ).fetchone()[0],
        "llm_adjudications": db.execute("SELECT COUNT(*) FROM adjudication").fetchone()[0],
        "verified_claims_with_object": db.execute("""
            SELECT COUNT(*) FROM assertion a JOIN claim c ON c.id=a.claim_id
            WHERE a.status='verified' AND c.object_id IS NOT NULL
        """).fetchone()[0],
    }

    report = {
        "counts": counts,
        "assertions_by_status": dict(status),
        "assertions_by_grade": dict(grade),
        "rejections_by_stage": dict(rejections),
        "evidence_by_locator": dict(locators),
        "sources_by_kind": dict(sources),
        "claims_by_predicate": dict(predicates),
        "checks": checks,
    }
    AUDIT_DIR.mkdir(exist_ok=True)
    (AUDIT_DIR / "v2_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (AUDIT_DIR / "v2_audit.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _duplicate_count(db: sqlite3.Connection) -> int:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in db.execute("SELECT id, name, kind FROM entity WHERE status='active'"):
        key = org_merge_key(row["name"]) if row["kind"] in ORG_KINDS else normalize_name(row["name"])
        groups[(row["kind"], key)].append(row["id"])
    return sum(1 for ids in groups.values() if len(ids) > 1)


def _markdown(report: dict) -> str:
    c = report["counts"]
    lines = ["# v2 Audit", "", "## Counts", "", "| Table | Rows |", "|---|---:|"]
    for key, value in c.items():
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Assertions", "", "| Status | Count |", "|---|---:|"]
    for key, value in sorted(report["assertions_by_status"].items(), key=lambda item: -item[1]):
        lines.append(f"| {key} | {value} |")
    lines += ["", "| Grade | Count |", "|---|---:|"]
    for key, value in sorted(report["assertions_by_grade"].items()):
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Evidence locator", "", "| Status | Rows |", "|---|---:|"]
    for key, value in sorted(report["evidence_by_locator"].items(), key=lambda item: -item[1]):
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Rejections", "", "| Stage | Count |", "|---|---:|"]
    for key, value in sorted(report["rejections_by_stage"].items(), key=lambda item: -item[1]):
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Invariants", "", "| Check | Value | Expected |", "|---|---:|---|"]
    expected = {
        "verified_without_located_evidence": 0,
        "verified_grade_none": 0,
        "located_evidence_without_sentence": 0,
        "evidence_without_doc": 0,
        "claims_without_object": 0,
        "duplicate_active_entities": 0,
        "documents_without_sentences": 0,
        "documents_without_hash": 0,
    }
    for key, value in report["checks"].items():
        lines.append(f"| {key} | {value} | {expected.get(key, 'informational')} |")
    lines += [
        "",
        "`duplicate_active_entities` compares exact normalised names within a kind;",
        "fuzzy duplicates are listed separately in `audit/entity_merge.json`.",
        "",
    ]
    return "\n".join(lines)


def check(db: sqlite3.Connection) -> list[str]:
    report = audit(db)
    failures = []
    for key, expected in {
        "verified_without_located_evidence": 0,
        "verified_grade_none": 0,
        "located_evidence_without_sentence": 0,
        "evidence_without_doc": 0,
        "claims_without_object": 0,
        "duplicate_active_entities": 0,
        "documents_without_sentences": 0,
        "documents_without_hash": 0,
    }.items():
        if report["checks"].get(key) != expected:
            failures.append(f"{key}={report['checks'].get(key)} (expected {expected})")
    for path in [GRAPH_DIR / "nodes.csv", GRAPH_DIR / "edges.csv", GRAPH_DIR / "graph.graphml",
                 WIKI_V2_DIR / "index.md", AUDIT_DIR / "v2_audit.md"]:
        if not path.exists():
            failures.append(f"missing artifact: {path}")
    return failures


def main() -> int:
    db = connect()
    failures = check(db)
    report = audit(db)
    print(json.dumps(report["checks"], indent=2))
    if failures:
        print("FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("v2 invariants hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

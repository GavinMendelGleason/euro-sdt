#!/usr/bin/env python3
"""Human review queue and decision recorder for the v2 assertion layer.

Examples:
  python scripts/review.py list --limit 50
  python scripts/review.py list --include-a --sample-a 50
  python scripts/review.py decide --claim-id c-... --decision rejected \
      --reviewer gavin --reason "quote names the parliamentary group, not the party"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from euro_sdt.v2.db import AUDIT_DIR, connect, now, uid
from euro_sdt.v2.graph import NETWORK_PREDICATES

BEST_EVIDENCE = """
    LEFT JOIN evidence e ON e.id = (
        SELECT e2.id FROM evidence e2
        WHERE e2.claim_id = c.id AND e2.locator_status = 'located'
        ORDER BY (e2.subject_mentioned + e2.object_mentioned + e2.role_mentioned) DESC,
                 length(e2.quote) ASC, e2.id LIMIT 1
    )
    LEFT JOIN source_document d ON d.id = e.doc_id
    LEFT JOIN adjudication adj ON adj.rowid = (
        SELECT MAX(rowid) FROM adjudication WHERE claim_id = c.id
    )
"""


def _model_disagreements() -> dict[str, tuple[str, str]]:
    path = AUDIT_DIR / "model_comparison.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            chat = row.get("chat_verdict", "")
            flash = row.get("flash_verdict", "")
            if chat and flash and chat != flash and "ERROR" not in (chat, flash):
                out[row["claim_id"]] = (chat, flash)
    return out


def _rows(db: sqlite3.Connection, include_a: bool, sample_a: int) -> list[dict]:
    sql = f"""
        SELECT a.claim_id, a.status, a.evidence_grade, a.n_sources, a.reason AS assertion_reason,
               c.subject_id, c.predicate, c.object_id, c.object_literal, c.role, c.role_raw,
               s.name AS subject_name, COALESCE(o.name, c.object_literal) AS object_display,
               e.quote, e.subject_context, e.notes, e.doc_id,
               d.title AS doc_title, d.url AS doc_url, d.local_path AS doc_path,
               adj.model AS adjudicator_model, adj.verdict AS adjudicator_verdict,
               adj.reason AS adjudicator_reason
        FROM assertion a
        JOIN claim c ON c.id = a.claim_id
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN entity o ON o.id = c.object_id
        {BEST_EVIDENCE}
        WHERE a.status = 'needs_review'
           OR (a.status = 'verified' AND a.evidence_grade IN ('B','C'))
    """
    rows = [dict(row) for row in db.execute(sql).fetchall()]
    if include_a:
        extra = db.execute(f"""
            SELECT a.claim_id, a.status, a.evidence_grade, a.n_sources, a.reason AS assertion_reason,
                   c.subject_id, c.predicate, c.object_id, c.object_literal, c.role, c.role_raw,
                   s.name AS subject_name, COALESCE(o.name, c.object_literal) AS object_display,
                   e.quote, e.subject_context, e.notes, e.doc_id,
                   d.title AS doc_title, d.url AS doc_url, d.local_path AS doc_path,
                   adj.model AS adjudicator_model, adj.verdict AS adjudicator_verdict,
                   adj.reason AS adjudicator_reason
            FROM assertion a
            JOIN claim c ON c.id = a.claim_id
            JOIN entity s ON s.id = c.subject_id
            LEFT JOIN entity o ON o.id = c.object_id
            {BEST_EVIDENCE}
            WHERE a.status = 'verified' AND a.evidence_grade = 'A'
              AND c.predicate IN ({",".join("?" for _ in NETWORK_PREDICATES)})
        """, tuple(sorted(NETWORK_PREDICATES))).fetchall()
        extra = sorted((dict(row) for row in extra),
                       key=lambda row: hashlib.sha1(row["claim_id"].encode()).hexdigest())
        rows.extend(extra[:sample_a])

    disagreements = _model_disagreements()
    for row in rows:
        score = 0
        if row["status"] == "needs_review":
            score += 50
        if row["evidence_grade"] == "C":
            score += 40
        elif row["evidence_grade"] == "B":
            score += 20
        elif row["evidence_grade"] == "A":
            score += 5
        if row["subject_context"] == "document":
            score += 15
        if row["notes"] and "recovered" in row["notes"]:
            score += 10
        if (row["n_sources"] or 0) <= 1:
            score += 5
        if row["predicate"] in NETWORK_PREDICATES:
            score += 5
        if row["claim_id"] in disagreements:
            score += 20
            row["model_disagreement"] = " | ".join(disagreements[row["claim_id"]])
        else:
            row["model_disagreement"] = ""
        row["priority"] = score
    rows.sort(key=lambda row: (-row["priority"], row["predicate"], row["subject_name"]))
    return rows


def list_queue(args) -> int:
    db = connect()
    rows = _rows(db, args.include_a, args.sample_a)
    if args.limit:
        rows = rows[:args.limit]
    AUDIT_DIR.mkdir(exist_ok=True)
    fields = [
        "priority", "claim_id", "status", "evidence_grade", "n_sources", "predicate",
        "subject_name", "object_display", "role", "quote", "doc_title", "doc_path",
        "doc_url", "subject_context", "notes", "adjudicator_model", "adjudicator_verdict",
        "adjudicator_reason", "model_disagreement",
    ]
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})

    counts = Counter(row["evidence_grade"] for row in rows)
    statuses = Counter(row["status"] for row in rows)
    lines = [
        "# Review Queue",
        "",
        f"Rows: {len(rows)}. Priority = uncertainty + weak context + model disagreement.",
        "",
        f"By grade: {dict(counts)}. By status: {dict(statuses)}.",
        "",
        "| Priority | Status | Grade | Subject | Predicate | Object | Model |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in rows[:60]:
        lines.append(
            f"| {row['priority']} | {row['status']} | {row['evidence_grade']} | "
            f"{row['subject_name']} | {row['predicate']} | {row['object_display']} | "
            f"{row.get('adjudicator_model') or ''} {row.get('adjudicator_verdict') or ''} |"
        )
    lines += [
        "",
        "Decide with:",
        "",
        "```bash",
        "python scripts/review.py decide --claim-id <id> --decision verified|rejected|needs_review \\",
        "  --reviewer <name> --reason '...'",
        "```",
    ]
    args.output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}.csv/.md ({len(rows)} rows)")
    print(f"grades: {dict(counts)} statuses: {dict(statuses)}")
    return 0


def decide(args) -> int:
    db = connect()
    db.execute("""CREATE TABLE IF NOT EXISTS review (
        id TEXT PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claim(id),
        decision TEXT NOT NULL, reviewer TEXT NOT NULL, reason TEXT, created_at TEXT NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_review_claim ON review(claim_id)")
    row = db.execute("SELECT id, status FROM assertion WHERE claim_id=?", (args.claim_id,)).fetchone()
    if not row:
        print(f"no assertion for claim {args.claim_id}")
        return 1
    db.execute(
        "UPDATE assertion SET status=?, reason=?, adjudicator='human', adjudicated_at=? WHERE claim_id=?",
        (args.decision, args.reason, now(), args.claim_id),
    )
    db.execute(
        "INSERT INTO review (id, claim_id, decision, reviewer, reason, created_at) VALUES (?,?,?,?,?,?)",
        (uid("rv-"), args.claim_id, args.decision, args.reviewer, args.reason, now()),
    )
    if args.decision == "rejected":
        rejection_id = "r-" + hashlib.sha1(f"{args.claim_id}|human_review".encode()).hexdigest()[:16]
        db.execute(
            "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
            (rejection_id, args.claim_id, "human_review", args.reason, now()),
        )
    db.commit()
    print(f"{args.claim_id}: {row['status']} -> {args.decision}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--limit", type=int, default=0)
    list_parser.add_argument("--include-a", action="store_true",
                             help="Include a sample of grade-A network claims")
    list_parser.add_argument("--sample-a", type=int, default=50)
    list_parser.add_argument("--output", type=Path, default=AUDIT_DIR / "review_queue")

    decide_parser = sub.add_parser("decide")
    decide_parser.add_argument("--claim-id", required=True)
    decide_parser.add_argument("--decision", required=True,
                               choices=["verified", "rejected", "needs_review"])
    decide_parser.add_argument("--reviewer", required=True)
    decide_parser.add_argument("--reason", required=True)

    args = parser.parse_args()
    if args.command == "list":
        return list_queue(args)
    return decide(args)


if __name__ == "__main__":
    raise SystemExit(main())

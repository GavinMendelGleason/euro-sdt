#!/usr/bin/env python3
"""Second-judge grade-A network claims with flash thinking on.

Grade A was passed by the deterministic gate but never adjudicated. This script
asks one independent model whether the quote supports the claim. A disagreement
moves the claim to needs_review; nothing is auto-promoted or auto-rejected.

Examples:
  python scripts/recheck_grade_a.py --dry-run --limit 100
  python scripts/recheck_grade_a.py --db euro_sdt_v2.db --workers 8
  python scripts/recheck_grade_a.py --all-predicates --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.adjudicate import _cache_key, _call, _load_cache, _prompt, _save_cache
from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, now, sha256_text
from euro_sdt.v2.graph import NETWORK_PREDICATES

BEST_EVIDENCE = """
    LEFT JOIN evidence e ON e.id = (
        SELECT e2.id FROM evidence e2
        WHERE e2.claim_id = c.id AND e2.locator_status = 'located'
        ORDER BY (e2.subject_mentioned + e2.object_mentioned + e2.role_mentioned) DESC,
                 length(e2.quote) ASC, e2.id LIMIT 1
    )
    LEFT JOIN source_document d ON d.id = e.doc_id
"""


def candidates(db: sqlite3.Connection, all_predicates: bool, limit: int | None):
    predicate_sql = "" if all_predicates else "AND c.predicate IN ({})".format(
        ",".join("?" for _ in NETWORK_PREDICATES)
    )
    params = () if all_predicates else tuple(sorted(NETWORK_PREDICATES))
    rows = db.execute(f"""
        SELECT a.claim_id, a.status, a.evidence_grade, a.n_sources,
               c.subject_id, c.predicate, c.object_id, c.object_literal, c.role, c.role_raw,
               s.name AS subject_name, COALESCE(o.name, c.object_literal) AS object_display,
               e.id AS evidence_id, e.quote, e.doc_id,
               d.title AS doc_title, d.url AS doc_url
        FROM assertion a
        JOIN claim c ON c.id = a.claim_id
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN entity o ON o.id = c.object_id
        {BEST_EVIDENCE}
        WHERE a.status = 'verified' AND a.evidence_grade = 'A'
          AND c.object_id IS NOT NULL {predicate_sql}
        ORDER BY a.claim_id
    """, params).fetchall()
    rows = sorted(rows, key=lambda row: hashlib.sha1(row["claim_id"].encode()).hexdigest())
    return rows[:limit] if limit else rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--all-predicates", action="store_true")
    parser.add_argument("--with-chat", action="store_true",
                        help="Also call deepseek-chat; require both models to support")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "grade_a_recheck")
    args = parser.parse_args()

    db = connect(args.db)
    rows = candidates(db, args.all_predicates, args.limit)
    print(f"candidates: {len(rows)}")

    cache = _load_cache()
    results: dict[str, dict] = {}
    tasks = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for row in rows:
            prompt = _prompt(row)
            prompt_hash = sha256_text(prompt)
            flash_key = _cache_key("deepseek-flash", row["claim_id"], prompt_hash, thinking=True)
            cached = cache.get(flash_key)
            if cached and cached.get("verdict") in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"):
                results[row["claim_id"]] = {
                    "flash_verdict": cached["verdict"], "flash_reason": cached.get("reason", ""),
                    "chat_verdict": "", "chat_reason": "", "prompt_hash": prompt_hash,
                }
                if args.with_chat:
                    try:
                        chat_verdict, chat_reason = _call(prompt, "deepseek-chat", False)
                    except Exception as exc:
                        chat_verdict, chat_reason = "ERROR", f"{type(exc).__name__}: {exc}"
                    results[row["claim_id"]]["chat_verdict"] = chat_verdict
                    results[row["claim_id"]]["chat_reason"] = chat_reason
                continue
            flash_task = pool.submit(_call, prompt, "deepseek-flash", True)
            chat_task = pool.submit(_call, prompt, "deepseek-chat", False) if args.with_chat else None
            tasks[flash_task] = (row, prompt_hash, flash_key, chat_task)

        for future in as_completed(tasks):
            row, prompt_hash, flash_key, chat_task = tasks[future]
            try:
                flash_verdict, flash_reason = future.result()
            except Exception as exc:
                flash_verdict, flash_reason = "ERROR", f"{type(exc).__name__}: {exc}"
            chat_verdict = chat_reason = ""
            if chat_task is not None:
                try:
                    chat_verdict, chat_reason = chat_task.result()
                except Exception as exc:
                    chat_verdict, chat_reason = "ERROR", f"{type(exc).__name__}: {exc}"
            results[row["claim_id"]] = {
                "flash_verdict": flash_verdict, "flash_reason": flash_reason,
                "chat_verdict": chat_verdict, "chat_reason": chat_reason,
                "prompt_hash": prompt_hash,
            }
            if flash_verdict != "ERROR":
                cache[flash_key] = {
                    "verdict": flash_verdict, "reason": flash_reason,
                    "model": "deepseek-flash", "claim_id": row["claim_id"],
                }
            if len(results) % 25 == 0:
                _save_cache(cache)
    _save_cache(cache)

    counts = Counter()
    out_rows = []
    for row in rows:
        item = results[row["claim_id"]]
        supported = item["flash_verdict"] == "SUPPORTED"
        if args.with_chat:
            supported = supported and item["chat_verdict"] == "SUPPORTED"
        action = "keep_verified" if supported else "needs_review"
        counts[action] += 1
        out_rows.append({
            "claim_id": row["claim_id"], "predicate": row["predicate"], "status": row["status"],
            "subject": row["subject_name"], "object": row["object_display"],
            "role": row["role_raw"] or row["role"] or "",
            "flash_verdict": item["flash_verdict"], "chat_verdict": item["chat_verdict"],
            "action": action, "flash_reason": item["flash_reason"],
            "chat_reason": item["chat_reason"], "quote": (row["quote"] or "")[:500],
        })

    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()) if out_rows else [])
        writer.writeheader()
        writer.writerows(out_rows)

    lines = [
        "# Grade A Second Judge",
        "",
        f"Candidates: {len(rows)}. Judge: `deepseek-flash` thinking on"
        + (" plus `deepseek-chat`." if args.with_chat else "."),
        "",
        "| Action | Count |",
        "|---|---:|",
    ]
    for action, n in counts.most_common():
        lines.append(f"| {action} | {n} |")
    lines += ["", "## Disagreements", ""]
    for item in out_rows:
        if item["action"] == "needs_review":
            lines.append(f"- **{item['subject']} — {item['predicate']} — {item['object']}** "
                         f"(flash {item['flash_verdict']}, chat {item['chat_verdict'] or 'n/a'})")
            lines.append(f"  - flash: {item['flash_reason'][:200]}")
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md")
    print(dict(counts))

    if args.dry_run:
        return 0

    for row in rows:
        item = results[row["claim_id"]]
        supported = item["flash_verdict"] == "SUPPORTED"
        if args.with_chat:
            supported = supported and item["chat_verdict"] == "SUPPORTED"
        action = "keep_verified" if supported else "needs_review"
        status = "verified" if action == "keep_verified" else "needs_review"
        reason = (
            "deterministic grade A confirmed by flash reasoning"
            if action == "keep_verified"
            else f"grade-A second judge did not confirm: flash={item['flash_verdict']}"
        )
        adjudicator = "deterministic+llm:deepseek-flash"
        db.execute(
            "UPDATE assertion SET status=?, reason=?, adjudicator=?, adjudicated_at=? WHERE claim_id=?",
            (status, reason, adjudicator, now(), row["claim_id"]),
        )
        adj_id = "adj-" + hashlib.sha1(f"{row['claim_id']}|grade_a|{item['flash_verdict']}".encode()).hexdigest()[:16]
        db.execute(
            "INSERT OR IGNORE INTO adjudication (id, claim_id, evidence_id, model, prompt_sha256, verdict, reason, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (adj_id, row["claim_id"], row["evidence_id"], "deepseek-flash", item["prompt_hash"],
             item["flash_verdict"], item["flash_reason"], now()),
        )
    db.commit()
    print("database updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

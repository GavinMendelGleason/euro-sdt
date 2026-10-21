#!/usr/bin/env python3
"""Re-check grade-C assertions with deepseek-flash thinking on.

Policy:
  both judges SUPPORTED          -> keep verified (two-model consensus)
  chat SUPPORTED, flash not      -> needs_review (do not auto-reject)
  chat UNSUPPORTED, flash SUPPORTED -> needs_review (conflict)
  both UNSUPPORTED               -> rejected
  anything else                  -> needs_review

Use --dry-run to write a report without changing the database.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.adjudicate import _cache_key, _call, _load_cache, _prompt, _save_cache
from euro_sdt.v2.db import AUDIT_DIR, V2_DB_PATH, connect, now, sha256_text, uid

BEST_EVIDENCE = """
    LEFT JOIN evidence e ON e.id = (
        SELECT e2.id FROM evidence e2
        WHERE e2.claim_id = c.id AND e2.locator_status = 'located'
        ORDER BY (e2.subject_mentioned + e2.object_mentioned + e2.role_mentioned) DESC,
                 length(e2.quote) ASC, e2.id LIMIT 1
    )
    LEFT JOIN source_document d ON d.id = e.doc_id
"""


def candidates(db: sqlite3.Connection, include_rejected: bool, limit: int | None):
    statuses = "('verified','needs_review')"
    if include_rejected:
        statuses = "('verified','needs_review','rejected')"
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
        WHERE a.evidence_grade = 'C' AND a.status IN {statuses}
        ORDER BY a.claim_id
    """).fetchall()
    rows = list(rows)
    if limit:
        rows = rows[:limit]
    return rows


def latest_verdict(db: sqlite3.Connection, claim_id: str) -> tuple[str, str, str]:
    row = db.execute(
        "SELECT model, verdict, reason FROM adjudication WHERE claim_id=? ORDER BY rowid DESC LIMIT 1",
        (claim_id,),
    ).fetchone()
    if row:
        return row["verdict"], row["reason"] or "", row["model"] or ""
    return "", "", ""


def action_for(chat: str, flash: str) -> str:
    if chat == "SUPPORTED" and flash == "SUPPORTED":
        return "keep_verified"
    if chat == "UNSUPPORTED" and flash == "UNSUPPORTED":
        return "reject"
    if chat == "SUPPORTED" and flash in ("UNSUPPORTED", "AMBIGUOUS"):
        return "needs_review"
    if chat == "UNSUPPORTED" and flash == "SUPPORTED":
        return "needs_review"
    return "needs_review"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(V2_DB_PATH))
    parser.add_argument("--include-rejected", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "grade_c_recheck")
    args = parser.parse_args()

    db = connect(args.db)
    rows = candidates(db, args.include_rejected, args.limit)
    print(f"candidates: {len(rows)}")
    cache = _load_cache()
    results: dict[str, dict] = {}
    tasks = {}

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for row in rows:
            prompt = _prompt(row)
            prompt_hash = sha256_text(prompt)
            flash_key = _cache_key("deepseek-flash", row["claim_id"], prompt_hash, thinking=True)
            chat_verdict, chat_reason, chat_model = latest_verdict(db, row["claim_id"])
            if not chat_verdict:
                chat_task = pool.submit(_call, prompt, "deepseek-chat", False)
            else:
                chat_task = None
            cached = cache.get(flash_key)
            if cached and cached.get("verdict") in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"):
                if not chat_verdict:
                    chat_verdict, chat_reason = _call(prompt, "deepseek-chat", False)
                    chat_model = "deepseek-chat"
                results[row["claim_id"]] = {
                    "flash_verdict": cached["verdict"], "flash_reason": cached.get("reason", ""),
                    "chat_verdict": chat_verdict, "chat_reason": chat_reason,
                    "chat_model": chat_model, "prompt_hash": prompt_hash,
                }
                continue
            flash_task = pool.submit(_call, prompt, "deepseek-flash", True)
            tasks[flash_task] = (row, prompt_hash, flash_key, chat_task, chat_verdict, chat_reason, chat_model)

        for future in as_completed(tasks):
            row, prompt_hash, flash_key, chat_task, chat_verdict, chat_reason, chat_model = tasks[future]
            try:
                flash_verdict, flash_reason = future.result()
            except Exception as exc:
                flash_verdict, flash_reason = "ERROR", f"{type(exc).__name__}: {exc}"
            if chat_task is not None:
                try:
                    chat_verdict, chat_reason = chat_task.result()
                except Exception as exc:
                    chat_verdict, chat_reason = "ERROR", f"{type(exc).__name__}: {exc}"
                chat_model = "deepseek-chat"
            results[row["claim_id"]] = {
                "flash_verdict": flash_verdict, "flash_reason": flash_reason,
                "chat_verdict": chat_verdict, "chat_reason": chat_reason,
                "chat_model": chat_model, "prompt_hash": prompt_hash,
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
    fieldnames = ["claim_id", "predicate", "grade", "status", "subject", "object", "role",
                  "chat_verdict", "flash_verdict", "action", "chat_reason", "flash_reason", "quote"]
    out_rows = []
    for row in rows:
        item = results[row["claim_id"]]
        action = action_for(item["chat_verdict"], item["flash_verdict"])
        counts[action] += 1
        out_rows.append({
            "claim_id": row["claim_id"], "predicate": row["predicate"], "grade": row["evidence_grade"],
            "status": row["status"], "subject": row["subject_name"], "object": row["object_display"],
            "role": row["role_raw"] or row["role"] or "", "chat_verdict": item["chat_verdict"],
            "flash_verdict": item["flash_verdict"], "action": action,
            "chat_reason": item["chat_reason"], "flash_reason": item["flash_reason"],
            "quote": (row["quote"] or "")[:500],
        })

    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    lines = [
        "# Grade C Recheck",
        "",
        f"Candidates: {len(rows)}. Second judge: `deepseek-flash` thinking on.",
        "",
        "| Action | Count |",
        "|---|---:|",
    ]
    for action, n in counts.most_common():
        lines.append(f"| {action} | {n} |")
    lines += ["", "## Disagreements", ""]
    for item in out_rows:
        if item["chat_verdict"] != item["flash_verdict"]:
            lines.append(f"- **{item['subject']} — {item['predicate']} — {item['object']}** "
                         f"(chat {item['chat_verdict']}, flash {item['flash_verdict']})")
            lines.append(f"  - chat: {item['chat_reason'][:180]}")
            lines.append(f"  - flash: {item['flash_reason'][:180]}")
    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}.csv/.md")
    print(dict(counts))

    if args.dry_run:
        return 0

    for row in rows:
        item = results[row["claim_id"]]
        action = action_for(item["chat_verdict"], item["flash_verdict"])
        claim_id = row["claim_id"]
        if action == "keep_verified":
            status, reason = "verified", "two-model consensus: chat and flash reasoning both supported"
        elif action == "reject":
            status, reason = "rejected", "two-model consensus: chat and flash reasoning both unsupported"
        else:
            status, reason = "needs_review", (
                f"second-judge disagreement: chat={item['chat_verdict']}, flash={item['flash_verdict']}"
            )
        adjudicator = "llm:consensus(chat+flash)" if action == "keep_verified" else "llm:deepseek-flash"
        db.execute(
            "UPDATE assertion SET status=?, reason=?, adjudicator=?, adjudicated_at=? WHERE claim_id=?",
            (status, reason, adjudicator, now(), claim_id),
        )
        adj_id = "adj-" + hashlib.sha1(f"{claim_id}|flash_recheck|{item['flash_verdict']}".encode()).hexdigest()[:16]
        db.execute(
            "INSERT OR IGNORE INTO adjudication (id, claim_id, evidence_id, model, prompt_sha256, verdict, reason, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (adj_id, claim_id, row["evidence_id"], "deepseek-flash", item["prompt_hash"],
             item["flash_verdict"], item["flash_reason"], now()),
        )
        if status == "rejected":
            rejection_id = "r-" + hashlib.sha1(f"{claim_id}|second_judge".encode()).hexdigest()[:16]
            db.execute(
                "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
                (rejection_id, claim_id, "second_judge", reason, now()),
            )
    db.commit()
    print("database updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

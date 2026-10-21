#!/usr/bin/env python3
"""Compare adjudication models on the same claims and prompts.

This does not modify the graph. It writes audit/model_comparison.csv and .md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.adjudicate import _call, _prompt
from euro_sdt.v2.db import AUDIT_DIR, connect

PREDICATES = [
    "member", "board_member", "chair", "affiliated_with", "from_country",
    "nominated_by", "served_on_commission", "held_portfolio", "educated_at",
    "employed_by", "advisory_board", "founder", "fellow", "attendee",
    "post_mandate_occupation", "held_position",
]
MODES = [
    ("chat", "deepseek-chat", False),
    ("flash", "deepseek-flash", False),
    ("flash_reasoning", "deepseek-flash", True),
]


def best_evidence_sql() -> str:
    return """
        SELECT c.id AS claim_id, c.predicate, c.role, c.role_raw, c.object_literal,
               s.name AS subject_name, COALESCE(o.name, c.object_literal) AS object_display,
               e.id AS evidence_id, e.quote, e.doc_id, d.title AS doc_title, d.url AS doc_url,
               a.status, a.evidence_grade
        FROM claim c
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN entity o ON o.id = c.object_id
        JOIN assertion a ON a.claim_id = c.id
        JOIN evidence e ON e.id = (
            SELECT e2.id FROM evidence e2 WHERE e2.claim_id = c.id AND e2.locator_status = 'located'
            ORDER BY (e2.subject_mentioned + e2.object_mentioned + e2.role_mentioned) DESC,
                     length(e2.quote) ASC, e2.id LIMIT 1
        )
        LEFT JOIN source_document d ON d.id = e.doc_id
        WHERE c.predicate = ?
        ORDER BY c.id
    """


def sample(db: sqlite3.Connection, per_predicate: int) -> list[sqlite3.Row]:
    rows: list[sqlite3.Row] = []
    for predicate in PREDICATES:
        candidates = db.execute(best_evidence_sql(), (predicate,)).fetchall()
        # Deterministic shuffle by claim id; keeps a reproducible sample.
        candidates.sort(key=lambda row: hashlib.sha1(row["claim_id"].encode()).hexdigest())
        rows.extend(candidates[:per_predicate])
    return rows


def run(rows: list[sqlite3.Row], workers: int) -> dict[str, dict[str, tuple[str, str]]]:
    results: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    tasks = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row in rows:
            prompt = _prompt(row)
            for label, model, thinking in MODES:
                tasks[pool.submit(_call, prompt, model, thinking)] = (row["claim_id"], label)
        for future in as_completed(tasks):
            claim_id, label = tasks[future]
            try:
                results[claim_id][label] = future.result()
            except Exception as exc:
                results[claim_id][label] = ("ERROR", f"{type(exc).__name__}: {exc}")
    return results


def write(rows: list[sqlite3.Row], results: dict, out: Path) -> None:
    AUDIT_DIR.mkdir(exist_ok=True)
    path = out.with_suffix(".csv")
    fields = ["claim_id", "predicate", "grade", "status", "subject", "object", "role", "quote"]
    for label, _, _ in MODES:
        fields += [f"{label}_verdict", f"{label}_reason"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = {
                "claim_id": row["claim_id"], "predicate": row["predicate"],
                "grade": row["evidence_grade"], "status": row["status"],
                "subject": row["subject_name"], "object": row["object_display"],
                "role": row["role_raw"] or row["role"] or "",
                "quote": (row["quote"] or "")[:500],
            }
            for label, _, _ in MODES:
                verdict, reason = results.get(row["claim_id"], {}).get(label, ("ERROR", "missing"))
                item[f"{label}_verdict"] = verdict
                item[f"{label}_reason"] = reason
            writer.writerow(item)

    agreements = {}
    for left in ("chat", "flash"):
        for right in ("flash", "flash_reasoning"):
            if left == right:
                continue
            pairs = [(results[r["claim_id"]].get(left, ("ERROR", ""))[0],
                      results[r["claim_id"]].get(right, ("ERROR", ""))[0]) for r in rows]
            agree = sum(1 for a, b in pairs if a == b and a != "ERROR")
            valid = sum(1 for a, b in pairs if a != "ERROR" and b != "ERROR")
            agreements[f"{left}_vs_{right}"] = {
                "agreement": agree, "valid": valid,
                "rate": round(agree / valid * 100, 1) if valid else 0,
            }

    per_predicate = defaultdict(Counter)
    for row in rows:
        chat = results[row["claim_id"]].get("chat", ("ERROR", ""))[0]
        flash = results[row["claim_id"]].get("flash", ("ERROR", ""))[0]
        per_predicate[row["predicate"]]["total"] += 1
        per_predicate[row["predicate"]]["agree"] += int(chat == flash and chat != "ERROR")
        per_predicate[row["predicate"]]["flash_supported"] += int(flash == "SUPPORTED")
        per_predicate[row["predicate"]]["chat_supported"] += int(chat == "SUPPORTED")

    lines = [
        "# Model Comparison",
        "",
        f"Claims: {len(rows)}. Models: `deepseek-chat`, `deepseek-flash` (thinking disabled), "
        "`deepseek-flash` (thinking enabled). Same prompt and evidence for every model.",
        "",
        "## Agreement",
        "",
        "| Pair | Agreement | Valid | Rate |",
        "|---|---:|---:|---:|",
    ]
    for pair, values in agreements.items():
        lines.append(f"| {pair} | {values['agreement']} | {values['valid']} | {values['rate']}% |")
    lines += ["", "## By predicate", "", "| Predicate | Claims | Chat/Flash agree | Chat supported | Flash supported |", "|---|---:|---:|---:|---:|"]
    for predicate, counts in sorted(per_predicate.items()):
        lines.append(f"| {predicate} | {counts['total']} | {counts['agree']} | {counts['chat_supported']} | {counts['flash_supported']} |")

    differences = []
    for row in rows:
        chat = results[row["claim_id"]].get("chat", ("ERROR", ""))
        flash = results[row["claim_id"]].get("flash", ("ERROR", ""))
        if chat[0] != flash[0]:
            differences.append((row, chat, flash))
    lines += ["", "## Disagreements (chat vs flash)", ""]
    for row, chat, flash in differences[:40]:
        lines.append(f"- **{row['subject_name']} — {row['predicate']} — {row['object_display']}** "
                     f"(grade {row['evidence_grade']}, current {row['status']})")
        lines.append(f"  - chat: {chat[0]} — {chat[1][:180]}")
        lines.append(f"  - flash: {flash[0]} — {flash[1][:180]}")

    (out.with_suffix(".md")).write_text("\n".join(lines), encoding="utf-8")
    (out.with_suffix(".json")).write_text(
        json.dumps({"agreement": agreements,
                    "per_predicate": {k: dict(v) for k, v in per_predicate.items()},
                    "claims": len(rows)}, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-predicate", type=int, default=8)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "model_comparison")
    args = parser.parse_args()
    db = connect()
    rows = sample(db, args.per_predicate)
    print(f"sampled {len(rows)} claims")
    results = run(rows, args.workers)
    write(rows, results, args.out)
    print(f"wrote {args.out}.csv/.md/.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

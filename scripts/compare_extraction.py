#!/usr/bin/env python3
"""Compare extraction models on the same documents and chunks."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from euro_sdt.v2.db import AUDIT_DIR, connect
from euro_sdt.v2.extract import _call, _chunks, _prompt, MODEL
from euro_sdt.v2.tokenizer import normalize_text

MODES = [
    ("chat", "deepseek-chat", False),
    ("flash", "deepseek-flash", False),
    ("flash_reasoning", "deepseek-flash", True),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--people", default="ursula-von-der-leyen,federica-mogherini,guillaume-faury,kaja-kallas")
    parser.add_argument("--chunks", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=AUDIT_DIR / "model_comparison_extraction")
    args = parser.parse_args()

    db = connect()
    work = []
    for person_id in [p.strip() for p in args.people.split(",") if p.strip()]:
        person = db.execute("SELECT id, name FROM entity WHERE id=?", (person_id,)).fetchone()
        if not person:
            continue
        doc = db.execute(
            "SELECT id, title FROM source_document WHERE kind='wikipedia' AND subject_id=? "
            "ORDER BY char_count DESC LIMIT 1", (person_id,)
        ).fetchone()
        if not doc:
            continue
        for index, chunk in enumerate(_chunks(db, doc["id"])):
            if index >= args.chunks:
                break
            work.append((person, doc, index, chunk))

    results = {}
    tasks = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for person, doc, index, chunk in work:
            prompt = _prompt(person["name"], chunk)
            for label, model, thinking in MODES:
                tasks[pool.submit(_call, prompt, model, thinking)] = (person["id"], doc["id"], index, label, chunk, prompt)

        for future in as_completed(tasks):
            person_id, doc_id, index, label, chunk, prompt = tasks[future]
            try:
                rows = future.result()
            except Exception as exc:
                rows = []
                error = f"{type(exc).__name__}: {exc}"
            else:
                error = ""
            text = " ".join(row["text"] for row in chunk)
            normalized = normalize_text(text)
            locatable = sum(1 for row in rows if normalize_text(row.get("evidence", "")) and normalize_text(row.get("evidence", ""))[:80] in normalized)
            results[(person_id, doc_id, index, label)] = {
                "rows": rows, "error": error, "locatable": locatable,
                "relations": Counter(row.get("relation") for row in rows),
            }

    lines = [
        "# Extraction Model Comparison",
        "",
        f"Documents: {len({w[1]['id'] for w in work})}; chunks: {len(work)}; "
        "same prompt and source text for every model.",
        "",
        "| Person | Chunk | Chat rows | Flash rows | Flash reasoning rows | Chat locatable | Flash locatable |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    csv_rows = []
    for person, doc, index, chunk in work:
        chat = results.get((person["id"], doc["id"], index, "chat"), {})
        flash = results.get((person["id"], doc["id"], index, "flash"), {})
        flash_r = results.get((person["id"], doc["id"], index, "flash_reasoning"), {})
        lines.append(
            f"| {person['name']} | {index} | {len(chat.get('rows', []))} | {len(flash.get('rows', []))} | "
            f"{len(flash_r.get('rows', []))} | {chat.get('locatable', 0)} | {flash.get('locatable', 0)} |"
        )
        for label, model, thinking in MODES:
            item = results.get((person["id"], doc["id"], index, label), {})
            for row in item.get("rows", []):
                csv_rows.append({
                    "person": person["name"], "doc_id": doc["id"], "chunk": index, "model": label,
                    "organisation": row.get("organisation", ""), "role": row.get("role", ""),
                    "relation": row.get("relation", ""), "evidence": row.get("evidence", ""),
                    "locatable": int(normalize_text(row.get("evidence", ""))[:80] in normalize_text(" ".join(s["text"] for s in chunk))),
                })
    lines += ["", "## Relation mix", "", "| Model | Relations |", "|---|---|"]
    for label, _, _ in MODES:
        counter = Counter()
        for item in results.values():
            pass
        for key, item in results.items():
            if key[3] == label:
                counter.update(item["relations"])
        lines.append(f"| {label} | {dict(counter)} |")
    lines += ["", "## Errors", ""]
    for key, item in results.items():
        if item.get("error"):
            lines.append(f"- {key}: {item['error']}")

    args.out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    with args.out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["person", "doc_id", "chunk", "model", "organisation", "role", "relation", "evidence", "locatable"])
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"wrote {args.out}.md/.csv ({len(work)} chunks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

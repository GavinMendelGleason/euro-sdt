"""LLM adjudication for evidence that the deterministic checks cannot settle.

The model is a judge, not an extractor: it receives one exact quote and one
claim. It cannot introduce new facts, and every verdict is stored with the
model name and prompt hash. Unsupported claims are rejected; the model never
overrides a missing quote.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .db import AUDIT_DIR, now, uid, sha256_text

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = os.environ.get("EURO_SDT_V2_MODEL", "deepseek-chat")
WORKERS = int(os.environ.get("EURO_SDT_V2_WORKERS", "4"))
CACHE_PATH = AUDIT_DIR / "llm_adjudication_cache.json"

PREDICATE_MEANING = {
    "member": "is a member of the organisation",
    "board_member": "serves on the board / as trustee / as supervisory director of the organisation",
    "advisory_board": "serves on the advisory board or as an advisor to the organisation",
    "chair": "chairs or presides over the organisation",
    "employed_by": "is employed by the organisation in an executive role",
    "founder": "founded or co-founded the organisation",
    "fellow": "is a fellow of the organisation",
    "attendee": "attended a meeting or event of the organisation (not membership)",
    "affiliated_with": "has a formal affiliation with the organisation",
    "educated_at": "studied at or attended the educational institution",
    "served_on_commission": "served on the named European Commission",
    "held_portfolio": "held the named portfolio as a European Commissioner",
    "from_country": "is from / a national of / born in the named country",
    "nominated_by": "was nominated or appointed by the named country or its government",
    "post_mandate_occupation": "took up the named occupation after leaving the Commission",
    "held_position": "held the named position",
    "studied_field": "studied the named academic field",
    "held_degree": "holds the named degree",
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


def _prompt(row: sqlite3.Row) -> str:
    meaning = PREDICATE_MEANING.get(row["predicate"], row["predicate"].replace("_", " "))
    quote = (row["quote"] or "").strip()
    if len(quote) > 1800:
        quote = quote[:1800] + " […]"
    role = row["role_raw"] or row["role"] or "(not stated)"
    return f"""You are a strict fact-checker for a citation-anchored elite-network dataset.

CLAIM
  Subject: {row['subject_name']}
  Relation: {row['predicate']} — {meaning}
  Object: {row['object_display']}
  Role as recorded: {role}
  Document: {row['doc_title'] or '(untitled)'} ({row['doc_url'] or 'no url'})

QUOTE (the exact source text):
  "{quote}"

DECIDE whether the quote supports the claim.

RULES
- SUPPORTED only if the quote itself states the relation, or directly entails it.
- Membership is not attendance. Attendance is not membership.
- An employer relationship is not a board seat. A board seat is not generic affiliation.
- For nominated_by, the quote must state nomination or appointment by that country or its government.
- For from_country, the quote must state nationality, citizenship, birth, or origin in that country.
- For served_on_commission, the quote must identify the specific Commission term.
- If the quote is a role list, the subject must be the person whose list it is; this is acceptable for that person's own CV or declaration.
- Do not use outside knowledge. If the quote is insufficient, answer AMBIGUOUS.
- Never answer SUPPORTED merely because the person and organisation are both mentioned.

Reply with JSON only:
{{"verdict": "SUPPORTED|UNSUPPORTED|AMBIGUOUS", "reason": "one sentence"}}
"""


def _call(prompt: str) -> tuple[str, str]:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        return "ERROR", "DEEPSEEK_API_KEY is not set"
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 180,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }).encode()
    req = __import__("urllib.request", fromlist=["Request"]).Request(
        API_URL,
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    last_error = ""
    for attempt in range(3):
        try:
            with __import__("urllib.request", fromlist=["urlopen"]).urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            content = content.replace("<|endoftext|>", "").strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(match.group(0) if match else content)
            verdict = str(parsed.get("verdict", "")).upper()
            reason = str(parsed.get("reason", ""))[:500]
            if verdict not in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"):
                return "ERROR", f"unparseable verdict: {content[:200]}"
            return verdict, reason
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            time.sleep(1.5 * (attempt + 1))
    return "ERROR", last_error


def _candidate_rows(db: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = db.execute("""
        SELECT a.claim_id, a.evidence_grade, a.status, c.predicate, c.role, c.role_raw,
               c.object_literal, c.subject_id, c.object_id,
               s.name AS subject_name, COALESCE(o.name, c.object_literal, '') AS object_display,
               e.id AS evidence_id, e.quote, e.doc_id, d.title AS doc_title, d.url AS doc_url,
               e.subject_mentioned, e.object_mentioned, e.role_mentioned
        FROM assertion a
        JOIN claim c ON c.id = a.claim_id
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN entity o ON o.id = c.object_id
        JOIN evidence e ON e.claim_id = c.id AND e.locator_status = 'located'
        LEFT JOIN source_document d ON d.id = e.doc_id
        WHERE (a.status = 'needs_review' OR (a.status = 'verified' AND a.evidence_grade = 'B'))
        ORDER BY a.claim_id, (e.subject_mentioned + e.object_mentioned + e.role_mentioned) DESC,
                 length(e.quote) ASC
    """).fetchall()
    best: dict[str, sqlite3.Row] = {}
    for row in rows:
        best.setdefault(row["claim_id"], row)
    return list(best.values())


def adjudicate(db: sqlite3.Connection, limit: int | None = None,
               workers: int = WORKERS) -> dict[str, int]:
    candidates = _candidate_rows(db)
    if limit:
        candidates = candidates[:limit]
    cache = _load_cache()
    results: dict[str, tuple[str, str]] = {}
    prompt_hashes: dict[str, str] = {}
    tasks = {}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for row in candidates:
            prompt = _prompt(row)
            prompt_hash = sha256_text(prompt)
            prompt_hashes[row["claim_id"]] = prompt_hash
            key = f"{row['claim_id']}:{prompt_hash[:16]}"
            cached = cache.get(key)
            if cached and cached.get("verdict") in ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"):
                results[row["claim_id"]] = (cached["verdict"], cached.get("reason", ""))
                continue
            tasks[pool.submit(_call, prompt)] = (row, prompt_hash, key)

        for future in as_completed(tasks):
            row, prompt_hash, key = tasks[future]
            try:
                verdict, reason = future.result()
            except Exception as exc:
                verdict, reason = "ERROR", f"{type(exc).__name__}: {exc}"
            if verdict == "ERROR":
                continue
            results[row["claim_id"]] = (verdict, reason)
            cache[key] = {"verdict": verdict, "reason": reason, "model": MODEL, "claim_id": row["claim_id"]}
            if len(results) % 25 == 0:
                _save_cache(cache)

    _save_cache(cache)

    counts = {"SUPPORTED": 0, "UNSUPPORTED": 0, "AMBIGUOUS": 0, "ERROR": 0}
    for row in candidates:
        verdict, reason = results.get(row["claim_id"], ("ERROR", "no verdict"))
        counts[verdict] += 1
        if verdict == "SUPPORTED":
            db.execute(
                "UPDATE assertion SET status='verified', reason=?, adjudicator=?, adjudicated_at=? WHERE claim_id=?",
                (reason, f"llm:{MODEL}", now(), row["claim_id"]),
            )
            adj_id = "adj-" + __import__("hashlib").sha1(
                f"{row['claim_id']}|{row['evidence_id']}|{verdict}".encode()
            ).hexdigest()[:16]
            db.execute(
                "INSERT OR IGNORE INTO adjudication (id, claim_id, evidence_id, model, prompt_sha256, verdict, reason, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (adj_id, row["claim_id"], row["evidence_id"], MODEL, prompt_hashes.get(row["claim_id"], ""), verdict, reason, now()),
            )
        elif verdict == "UNSUPPORTED":
            db.execute(
                "UPDATE assertion SET status='rejected', reason=?, adjudicator=?, adjudicated_at=? WHERE claim_id=?",
                (reason, f"llm:{MODEL}", now(), row["claim_id"]),
            )
            adj_id = "adj-" + __import__("hashlib").sha1(
                f"{row['claim_id']}|{row['evidence_id']}|{verdict}".encode()
            ).hexdigest()[:16]
            db.execute(
                "INSERT OR IGNORE INTO adjudication (id, claim_id, evidence_id, model, prompt_sha256, verdict, reason, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (adj_id, row["claim_id"], row["evidence_id"], MODEL, prompt_hashes.get(row["claim_id"], ""), verdict, reason, now()),
            )
            db.execute(
                "INSERT OR IGNORE INTO rejection (id, claim_id, stage, reason, created_at) VALUES (?,?,?,?,?)",
                ("r-" + __import__("hashlib").sha1(f"{row['claim_id']}|llm_adjudication".encode()).hexdigest()[:16], row["claim_id"], "llm_adjudication", reason, now()),
            )
        elif verdict == "AMBIGUOUS":
            db.execute(
                "UPDATE assertion SET status='needs_review', reason=?, adjudicator=?, adjudicated_at=? WHERE claim_id=?",
                (reason, f"llm:{MODEL}", now(), row["claim_id"]),
            )
            adj_id = "adj-" + __import__("hashlib").sha1(
                f"{row['claim_id']}|{row['evidence_id']}|{verdict}".encode()
            ).hexdigest()[:16]
            db.execute(
                "INSERT OR IGNORE INTO adjudication (id, claim_id, evidence_id, model, prompt_sha256, verdict, reason, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (adj_id, row["claim_id"], row["evidence_id"], MODEL, prompt_hashes.get(row["claim_id"], ""), verdict, reason, now()),
            )
    db.commit()
    return counts

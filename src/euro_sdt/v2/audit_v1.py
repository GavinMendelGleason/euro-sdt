"""Reproduce the v1 evidence audit."""

from __future__ import annotations

import csv
import difflib
import html
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

from .db import AUDIT_DIR, PROJECT_ROOT, V1_DB_PATH
from .tokenizer import sentence_spans

SOURCES = PROJECT_ROOT / "sources"


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip().lower()


def _doc_cache() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in SOURCES.rglob("*.txt"):
        out.setdefault(_slug(path.stem), str(path))
    return out


def _resolve(cid: str, url: str | None, source_name: str, docs: dict[str, str]) -> str | None:
    candidates: list[str] = []
    if url and "wikipedia.org/wiki/" in url:
        candidates.append(_slug(url.rsplit("/wiki/", 1)[-1].replace("_", " ")))
    for prefix in ("cit-wiki-mep-mep-", "cit-wiki-mep-", "cit-wiki-corp-", "cit-wiki-"):
        if cid.startswith(prefix):
            candidates.append(_slug(cid[len(prefix):]))
    if source_name:
        candidates.append(_slug(re.sub(r"^Wikipedia (article|page):\s*", "", source_name)))
    for candidate in candidates:
        if candidate in docs:
            return docs[candidate]
    for candidate in candidates:
        match = difflib.get_close_matches(candidate, list(docs), n=1, cutoff=0.9)
        if match:
            return docs[match[0]]
    return None


def audit(v1_path: Path = V1_DB_PATH) -> dict:
    db = sqlite3.connect(v1_path)
    db.row_factory = sqlite3.Row
    docs = _doc_cache()
    text_cache: dict[str, str] = {}
    sentence_cache: dict[str, list] = {}

    counts = {
        "facts": db.execute("SELECT COUNT(*) FROM fact").fetchone()[0],
        "entities": db.execute("SELECT COUNT(*) FROM entity").fetchone()[0],
        "citations": db.execute("SELECT COUNT(*) FROM citation").fetchone()[0],
        "provenance": db.execute("SELECT COUNT(*) FROM provenance").fetchone()[0],
        "facts_without_provenance": db.execute(
            "SELECT COUNT(*) FROM fact f WHERE NOT EXISTS (SELECT 1 FROM provenance p WHERE p.fact_id=f.id)"
        ).fetchone()[0],
        "facts_verified": db.execute("SELECT COUNT(*) FROM fact WHERE verified_at IS NOT NULL").fetchone()[0],
        "facts_confirmed": db.execute("SELECT COUNT(*) FROM fact WHERE confidence='confirmed'").fetchone()[0],
        "affiliation_edges": db.execute(
            "SELECT COUNT(*) FROM fact WHERE predicate IN ('affiliated_with','member_of')"
        ).fetchone()[0],
        "affiliated_with_verified": db.execute(
            "SELECT COUNT(*) FROM fact WHERE predicate='affiliated_with' AND verified_at IS NOT NULL"
        ).fetchone()[0],
        "member_of_verified": db.execute(
            "SELECT COUNT(*) FROM fact WHERE predicate='member_of' AND verified_at IS NOT NULL"
        ).fetchone()[0],
        "distinct_affiliation_orgs": db.execute(
            "SELECT COUNT(DISTINCT object) FROM fact WHERE predicate IN ('affiliated_with','member_of')"
        ).fetchone()[0],
        "degree_one_orgs": db.execute(
            "SELECT COUNT(*) FROM (SELECT object, COUNT(DISTINCT entity_id) n FROM fact "
            "WHERE predicate IN ('affiliated_with','member_of') GROUP BY 1 HAVING n=1)"
        ).fetchone()[0],
        "classification_facts": db.execute("SELECT COUNT(*) FROM fact WHERE predicate='classified_as'").fetchone()[0],
    }
    counts["classification_llm"] = db.execute(
        "SELECT COUNT(*) FROM fact f JOIN provenance p ON p.fact_id=f.id "
        "JOIN citation c ON c.id=p.citation_id WHERE f.predicate='classified_as' AND c.source_type='llm'"
    ).fetchone()[0]
    counts["classification_dataset"] = db.execute(
        "SELECT COUNT(*) FROM fact f JOIN provenance p ON p.fact_id=f.id "
        "JOIN citation c ON c.id=p.citation_id WHERE f.predicate='classified_as' AND c.source_type='dataset'"
    ).fetchone()[0]
    counts["citation_missing_rows"] = db.execute(
        "SELECT COUNT(*) FROM provenance p LEFT JOIN citation c ON c.id=p.citation_id WHERE c.id IS NULL"
    ).fetchone()[0]
    counts["zero_fact_entities"] = db.execute(
        "SELECT COUNT(*) FROM entity e WHERE NOT EXISTS (SELECT 1 FROM fact f WHERE f.entity_id=e.id)"
    ).fetchone()[0]
    counts["isolated_entities"] = db.execute(
        "SELECT COUNT(*) FROM entity e WHERE NOT EXISTS (SELECT 1 FROM fact f WHERE f.entity_id=e.id) "
        "AND NOT EXISTS (SELECT 1 FROM fact f2 WHERE f2.object=e.id AND f2.object_type IN ('entity','entity_id'))"
    ).fetchone()[0]

    tiers = Counter()
    rows_out = []
    for row in db.execute("""
        SELECT p.id, p.fact_id, p.quote_text, p.phrase_index, p.citation_id,
               f.predicate, f.entity_id, f.object, f.object_type, c.source_type, c.url, c.source_name
        FROM provenance p JOIN fact f ON f.id=p.fact_id
        LEFT JOIN citation c ON c.id=p.citation_id
    """):
        quote = row["quote_text"] or ""
        status = ""
        if row["source_type"] is None:
            status = "citation-missing"
        elif row["source_type"] == "llm":
            status = "llm-self-classification"
        elif quote.startswith('Name "'):
            status = "name-presence"
        elif " → " in quote or " — " in quote or "classified as" in quote:
            status = "synthetic"
        elif row["phrase_index"] is None or row["phrase_index"] < 0:
            status = "no-index"
        else:
            path = _resolve(row["citation_id"], row["url"], row["source_name"] or "", docs)
            if not path:
                status = "source-missing"
            else:
                if path not in text_cache:
                    text_cache[path] = Path(path).read_text(encoding="utf-8", errors="replace")
                    sentence_cache[path] = sentence_spans(text_cache[path])
                text = text_cache[path]
                nq = _norm(quote)
                if nq[:120] not in _norm(text):
                    status = "quote-not-in-source"
                else:
                    spans = sentence_cache[path]
                    idx = row["phrase_index"]
                    if idx < len(spans) and (
                        _norm(spans[idx].text)[:120] == nq[:120]
                        or nq[:80] in _norm(spans[idx].text)
                        or _norm(spans[idx].text)[:80] in nq
                    ):
                        status = "located"
                    else:
                        status = "index-mismatch"
        tiers[status] += 1
        rows_out.append({
            "provenance_id": row["id"], "fact_id": row["fact_id"], "predicate": row["predicate"],
            "status": status, "phrase_index": row["phrase_index"],
            "citation_id": row["citation_id"], "quote": quote[:300],
        })

    AUDIT_DIR.mkdir(exist_ok=True)
    with (AUDIT_DIR / "v1_provenance.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)

    total = sum(tiers.values())
    report = {
        "counts": counts,
        "evidence_tiers": dict(tiers),
        "total_provenance": total,
        "summary": {
            "quote_present_in_source": tiers.get("located", 0) + tiers.get("index-mismatch", 0),
            "quote_present_share": round((tiers.get("located", 0) + tiers.get("index-mismatch", 0)) / total * 100, 1),
            "index_resolves_under_v2_tokenizer": tiers.get("located", 0),
            "index_resolves_share": round(tiers.get("located", 0) / total * 100, 1),
            "no_sentence_evidence": sum(tiers.get(k, 0) for k in (
                "llm-self-classification", "synthetic", "name-presence", "no-index", "citation-missing")),
            "no_sentence_evidence_share": round(sum(tiers.get(k, 0) for k in (
                "llm-self-classification", "synthetic", "name-presence", "no-index", "citation-missing")) / total * 100, 1),
        },
    }
    (AUDIT_DIR / "v1_baseline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (AUDIT_DIR / "v1_baseline.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _markdown(report: dict) -> str:
    counts = report["counts"]
    total = report["total_provenance"]
    lines = [
        "# v1 Baseline Audit",
        "",
        "Reproduced by `scripts/audit_v1.py` from `euro_sdt.db` and `sources/`.",
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in counts.items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines += ["", "## Summary", "", "| Metric | Value |", "|---|---:|"]
    for key, value in report["summary"].items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines += ["", "## Evidence tiers", "", "| Tier | Rows | Share |", "|---|---:|---:|"]
    for key, value in sorted(report["evidence_tiers"].items(), key=lambda item: -item[1]):
        lines.append(f"| {key} | {value} | {value / total * 100:.1f}% |")
    lines += [
        "",
        "`located` means the quote appears at the recorded sentence position under a",
        "deterministic sentence split of the cited `.txt`. It is an upper bound on",
        "locatability, not a check that the sentence entails the relation.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    audit()
    print("wrote audit/v1_baseline.md")

"""Write the human-readable v1/v2 comparison report."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter

from .db import AUDIT_DIR, GRAPH_DIR, connect


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def generate_report(db: sqlite3.Connection) -> dict:
    v1 = _load(AUDIT_DIR / "v1_baseline.json", {})
    v2 = _load(AUDIT_DIR / "v2_audit.json", {})
    graph = _load(GRAPH_DIR / "metrics.json", {})
    if not v1 or not v2:
        # Generate the audits if the user has not run them yet.
        from .audit_v1 import audit as audit_v1
        from .audit_v2 import audit as audit_v2
        if not v1:
            v1 = audit_v1()
        if not v2:
            v2 = audit_v2(db)
        graph = _load(GRAPH_DIR / "metrics.json", graph)

    preds = db.execute("""
        SELECT c.predicate, a.status, COUNT(*) n
        FROM assertion a JOIN claim c ON c.id=a.claim_id
        GROUP BY 1,2 ORDER BY 1,2
    """).fetchall()
    sources = db.execute("SELECT kind, COUNT(*), SUM(char_count) FROM source_document GROUP BY 1 ORDER BY 2 DESC").fetchall()
    rejections = db.execute("SELECT stage, COUNT(*) FROM rejection GROUP BY 1 ORDER BY 2 DESC").fetchall()
    adjudications = db.execute("SELECT verdict, COUNT(*) FROM adjudication GROUP BY 1 ORDER BY 2 DESC").fetchall()

    lines = [
        "# Euro-SDT v2 Report",
        "",
        "Generated from `euro_sdt_v2.db`, `audit/v1_baseline.json`, and `graph/metrics.json`.",
        "",
        "## v1 to v2",
        "",
        "| Metric | v1 | v2 |",
        "|---|---:|---:|",
        f"| Assertions / facts | {v1.get('counts', {}).get('facts', 0)} | {v2.get('counts', {}).get('assertion', 0)} |",
        f"| Verified | {v1.get('counts', {}).get('facts_verified', 0)} | {v2.get('assertions_by_status', {}).get('verified', 0)} |",
        f"| Needs review | — | {v2.get('assertions_by_status', {}).get('needs_review', 0)} |",
        f"| Rejected | — | {v2.get('assertions_by_status', {}).get('rejected', 0)} |",
        f"| Source documents | 0 hashed | {v2.get('counts', {}).get('source_document', 0)} hashed |",
        f"| Sentences | 0 | {v2.get('counts', {}).get('sentence', 0)} |",
        "",
        "The v1 counts are not directly comparable: v1 called every row `confirmed`,",
        "and 30.1% of its provenance rows had no sentence evidence. v2 reports the",
        "verified subset and keeps rejected candidates in `rejection`.",
        "",
        "## Assertions",
        "",
        "| Status | Grade | Count |",
        "|---|---|---:|",
    ]
    for row in db.execute("SELECT status, evidence_grade, COUNT(*) FROM assertion GROUP BY 1,2 ORDER BY 1,2"):
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
    lines += ["", "## Predicate results", "", "| Predicate | Status | Count |", "|---|---|---:|"]
    for pred, status, n in preds:
        lines.append(f"| {pred} | {status} | {n} |")
    runs = db.execute("SELECT kind, model, started_at, finished_at, params_json FROM run ORDER BY started_at").fetchall()
    extracted = db.execute("SELECT COUNT(*) FROM claim WHERE extractor='v2_llm'").fetchone()[0]
    lines += ["", "## Runs", "", "| Kind | Model | Started | Finished |", "|---|---|---|---|"]
    for run in runs:
        lines.append(f"| {run[0]} | {run[1] or ''} | {run[2]} | {run[3] or ''} |")
    lines += ["", f"Claims from full-document extraction: **{extracted}**.", ""]
    lines += ["", "## Evidence and adjudication", "", "| Rejection stage | Count |", "|---|---:|"]
    for stage, n in rejections:
        lines.append(f"| {stage} | {n} |")
    lines += ["", "| LLM verdict | Count |", "|---|---:|"]
    for verdict, n in adjudications:
        lines.append(f"| {verdict} | {n} |")
    lines += ["", "## Sources", "", "| Kind | Documents | Characters |", "|---|---:|---:|"]
    for kind, n, chars in sources:
        lines.append(f"| {kind} | {n} | {chars or 0} |")
    if graph:
        allm = graph.get("all_verified", {})
        net = graph.get("network_only", {})
        lines += [
            "", "## Graph", "",
            "| Metric | All verified | Network only |",
            "|---|---:|---:|",
            f"| Nodes | {allm.get('nodes', 0)} | {net.get('nodes', 0)} |",
            f"| Edges | {allm.get('edges', 0)} | {net.get('edges', 0)} |",
            f"| Largest component | {allm.get('components', {}).get('largest', 0)} | {net.get('components', {}).get('largest', 0)} |",
            f"| Degree-1 nodes | {allm.get('degree', {}).get('degree_1', 0)} | {net.get('degree', {}).get('degree_1', 0)} |",
            "", "### Edges by class", "", "| Class | Edges |", "|---|---:|",
        ]
        for key, value in sorted(allm.get("edges_by_class", {}).items()):
            lines.append(f"| {key} | {value} |")
        lines += ["", "### Top hubs", "", "| Entity | Kind | Degree |", "|---|---|---:|"]
        for hub in allm.get("top_hubs", [])[:12]:
            lines.append(f"| {hub.get('name')} | {hub.get('kind')} | {hub.get('degree')} |")
    lines += [
        "", "## Remaining limitations", "",
        "- MEP and corporate Wikipedia coverage is incomplete; claims without a local",
        "  source document are rejected rather than assigned a guessed quote.",
        "- `revolving_door` documents are treated as summaries, not primary sentences;",
        "  they are excluded from `served_on_commission` recovery.",
        "- Organisation classifications remain a manually researched seed. They are",
        "  marked `manual_seed` and are not counted as verified assertions.",
        "- `post_mandate_occupation` coverage remains low because the source corpus",
        "  contains summaries rather than the underlying ethics decisions.",
        "",
    ]
    text = "\n".join(lines)
    (AUDIT_DIR / "v2_report.md").write_text(text, encoding="utf-8")
    return {"report": str(AUDIT_DIR / "v2_report.md")}


def main() -> int:
    generate_report(connect())
    print("wrote audit/v2_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

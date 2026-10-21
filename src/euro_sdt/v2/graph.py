"""Export the verified assertion graph and compute network metrics.

The analysis artifact is a pair of CSVs plus GraphML, not an Obsidian
screenshot. Edge class and evidence grade are attributes so every metric can be
recomputed on a filtered graph.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from .db import GRAPH_DIR

NETWORK_PREDICATES = {
    "member", "board_member", "advisory_board", "chair", "founder", "fellow",
    "affiliated_with", "attendee",
}
OCCUPATIONAL_PREDICATES = {"employed_by", "held_position", "post_mandate_occupation"}
EDUCATION_PREDICATES = {"educated_at", "studied_field", "held_degree"}
INSTITUTIONAL_PREDICATES = {"served_on_commission"}


def edge_class(predicate: str) -> str:
    if predicate in NETWORK_PREDICATES:
        return "network"
    if predicate in OCCUPATIONAL_PREDICATES:
        return "occupational"
    if predicate in EDUCATION_PREDICATES:
        return "education"
    if predicate in INSTITUTIONAL_PREDICATES:
        return "institutional"
    return "other"


def _rows(db: sqlite3.Connection, grade_filter: str | None = None):
    sql = """
        SELECT a.claim_id, a.evidence_grade, a.n_sources,
               c.subject_id, c.predicate, c.object_id, c.object_literal, c.role, c.role_raw,
               c.start_date, c.end_date,
               s.name AS subject_name, s.kind AS subject_kind, s.category AS subject_category,
               s.country AS subject_country, s.status AS subject_status,
               o.name AS object_name, o.kind AS object_kind, o.category AS object_category,
               o.country AS object_country, o.status AS object_status,
               e.quote, e.doc_id, d.url AS doc_url, d.title AS doc_title,
               d.local_path AS doc_path, d.kind AS doc_kind, d.text_sha256 AS doc_sha256
        FROM assertion a
        JOIN claim c ON c.id = a.claim_id
        JOIN entity s ON s.id = c.subject_id
        LEFT JOIN entity o ON o.id = c.object_id AND o.status = 'active'
        LEFT JOIN evidence e ON e.id = (
            SELECT e2.id FROM evidence e2
            WHERE e2.claim_id = c.id AND e2.locator_status = 'located'
            ORDER BY (e2.subject_mentioned + e2.object_mentioned + e2.role_mentioned) DESC,
                     length(e2.quote) ASC, e2.id
            LIMIT 1
        )
        LEFT JOIN source_document d ON d.id = e.doc_id
        WHERE a.status = 'verified' AND s.status = 'active'
          AND (c.object_id IS NULL OR o.id IS NOT NULL)
    """
    params: tuple = ()
    if grade_filter:
        sql += " AND a.evidence_grade = ?"
        params = (grade_filter,)
    sql += " ORDER BY c.predicate, s.name"
    return db.execute(sql, params).fetchall()


def _components(nodes: set[str], edges: list[tuple[str, str]]) -> list[int]:
    parent = {n: n for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in edges:
        if a in parent and b in parent:
            union(a, b)
    sizes = Counter(find(n) for n in nodes)
    return sorted(sizes.values(), reverse=True)


def _metrics(nodes: dict[str, dict], edges: list[dict]) -> dict:
    pairs = {(e["source"], e["target"]) for e in edges}
    neighbours: dict[str, set[str]] = defaultdict(set)
    for source, target in pairs:
        neighbours[source].add(target)
        neighbours[target].add(source)
    degrees = [len(v) for v in neighbours.values()]
    comps = _components(set(nodes), list(pairs))
    by_class = Counter(e["edge_class"] for e in edges)
    by_predicate = Counter(e["predicate"] for e in edges)
    by_grade = Counter(e["grade"] for e in edges)
    top = sorted(neighbours.items(), key=lambda item: (-len(item[1]), nodes.get(item[0], {}).get("name", "")))[:20]
    mixing = Counter((nodes[e["source"]]["kind"], nodes[e["target"]]["kind"]) for e in edges if e["source"] in nodes and e["target"] in nodes)
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "unique_pairs": len(pairs),
        "edges_by_class": dict(by_class),
        "edges_by_predicate": dict(by_predicate),
        "edges_by_grade": dict(by_grade),
        "degree": {
            "max": max(degrees) if degrees else 0,
            "mean": round(sum(degrees) / len(degrees), 2) if degrees else 0,
            "degree_1": sum(1 for d in degrees if d == 1),
            "degree_ge_3": sum(1 for d in degrees if d >= 3),
        },
        "components": {
            "count": len(comps),
            "largest": comps[0] if comps else 0,
            "singletons": sum(1 for c in comps if c == 1),
        },
        "top_hubs": [
            {"id": node_id, "name": nodes.get(node_id, {}).get("name", node_id),
             "kind": nodes.get(node_id, {}).get("kind"), "degree": len(ns)}
            for node_id, ns in top
        ],
        "kind_mixing": {f"{a}->{b}": n for (a, b), n in mixing.most_common(12)},
    }


def _bipartite_projection(edges: list[dict], nodes: dict[str, dict]) -> list[dict]:
    org_people: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        src, dst = edge["source"], edge["target"]
        if nodes.get(src, {}).get("kind") == "person" and nodes.get(dst, {}).get("kind") in ("organisation", "institution"):
            org_people[dst].add(src)
        elif nodes.get(dst, {}).get("kind") == "person" and nodes.get(src, {}).get("kind") in ("organisation", "institution"):
            org_people[src].add(dst)
    pair_counts: Counter = Counter()
    for people in org_people.values():
        people = sorted(people)
        for i, a in enumerate(people):
            for b in people[i + 1:]:
                pair_counts[(a, b)] += 1
    top = []
    for (a, b), n in pair_counts.most_common(25):
        top.append({"a": nodes.get(a, {}).get("name", a), "b": nodes.get(b, {}).get("name", b), "shared_orgs": n})
    return top


def build_graph(db: sqlite3.Connection, output_dir: Path = GRAPH_DIR) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _rows(db)
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple] = set()

    for row in rows:
        if not row["object_id"]:
            continue
        subject = row["subject_id"]
        obj = row["object_id"]
        if subject not in nodes:
            nodes[subject] = {
                "id": subject, "name": row["subject_name"], "kind": row["subject_kind"],
                "category": row["subject_category"], "country": row["subject_country"],
                "status": row["subject_status"],
            }
        if obj not in nodes:
            nodes[obj] = {
                "id": obj, "name": row["object_name"], "kind": row["object_kind"],
                "category": row["object_category"], "country": row["object_country"],
                "status": row["object_status"],
            }
        key = (subject, obj, row["predicate"], row["role"] or "")
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append({
            "source": subject,
            "target": obj,
            "predicate": row["predicate"],
            "edge_class": edge_class(row["predicate"]),
            "role": row["role"] or "",
            "role_raw": row["role_raw"] or "",
            "start_date": row["start_date"] or "",
            "end_date": row["end_date"] or "",
            "grade": row["evidence_grade"],
            "n_sources": row["n_sources"],
            "quote": (row["quote"] or "").replace("\n", " "),
            "doc_id": row["doc_id"] or "",
            "doc_title": row["doc_title"] or "",
            "doc_path": row["doc_path"] or "",
            "doc_kind": row["doc_kind"] or "",
            "doc_sha256": row["doc_sha256"] or "",
            "source_url": row["doc_url"] or "",
        })

    degree = Counter()
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    for node_id, node in nodes.items():
        node["degree"] = degree[node_id]

    with (output_dir / "nodes.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "name", "kind", "category", "country", "status", "degree"])
        writer.writeheader()
        writer.writerows(sorted(nodes.values(), key=lambda n: (n["kind"], n["name"])))

    fields = ["source", "target", "predicate", "edge_class", "role", "role_raw", "start_date", "end_date",
              "grade", "n_sources", "quote", "doc_id", "doc_title", "doc_kind", "doc_path", "doc_sha256",
              "source_url"]
    with (output_dir / "edges.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(edges)

    _write_graphml(output_dir / "graph.graphml", nodes, edges)

    verified_with_object = db.execute(
        "SELECT COUNT(*) FROM assertion a JOIN claim c ON c.id=a.claim_id "
        "WHERE a.status='verified' AND c.object_id IS NOT NULL"
    ).fetchone()[0]
    metrics = {
        "excluded_quarantined_endpoints": max(0, verified_with_object - len(edges)),
        "all_verified": _metrics(nodes, edges),
        "grade_a_only": _metrics(
            {n: v for n, v in nodes.items() if any(e["source"] == n and e["grade"] == "A" or e["target"] == n and e["grade"] == "A" for e in edges)},
            [e for e in edges if e["grade"] == "A"],
        ),
        "network_only": _metrics(
            {n: v for n, v in nodes.items()
             if any((e["source"] == n or e["target"] == n) and e["edge_class"] == "network" for e in edges)},
            [e for e in edges if e["edge_class"] == "network"],
        ),
        "co_affiliation": _bipartite_projection([e for e in edges if e["edge_class"] == "network"], nodes),
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "report.md").write_text(_report(metrics, edges), encoding="utf-8")
    return metrics


def _write_graphml(path: Path, nodes: dict[str, dict], edges: list[dict]) -> None:
    node_keys = [("name", "string"), ("kind", "string"), ("category", "string"), ("country", "string"), ("status", "string"), ("degree", "int")]
    edge_keys = [("predicate", "string"), ("edge_class", "string"), ("role", "string"), ("grade", "string"),
                 ("n_sources", "int"), ("doc_id", "string"), ("doc_title", "string"), ("doc_path", "string"),
                 ("source_url", "string"), ("quote", "string")]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    for key, typ in node_keys:
        lines.append(f'  <key id="n_{key}" for="node" attr.name="{key}" attr.type="{typ}"/>')
    for key, typ in edge_keys:
        lines.append(f'  <key id="e_{key}" for="edge" attr.name="{key}" attr.type="{typ}"/>')
    lines.append('  <graph id="euro-sdt-v2" edgedefault="directed">')
    for node in nodes.values():
        lines.append(f'    <node id={quoteattr(node["id"])}>')
        for key, _ in node_keys:
            value = node.get(key, "")
            lines.append(f'      <data key="n_{key}">{escape(str(value))}</data>')
        lines.append('    </node>')
    for i, edge in enumerate(edges):
        lines.append(f'    <edge id="e{i}" source={quoteattr(edge["source"])} target={quoteattr(edge["target"])}>')
        for key, _ in edge_keys:
            value = edge.get(key, "")
            lines.append(f'      <data key="e_{key}">{escape(str(value))}</data>')
        lines.append('    </edge>')
    lines.append('  </graph>')
    lines.append('</graphml>')
    path.write_text("\n".join(lines), encoding="utf-8")


def _report(metrics: dict, edges: list[dict]) -> str:
    allm = metrics["all_verified"]
    net = metrics["network_only"]
    lines = [
        "# Verified Elite Graph",
        "",
        "Generated from `euro_sdt_v2.db`. Only `assertion.status = 'verified'` appears here.",
        "",
        "## Summary",
        "",
        "| Metric | All verified | Grade A only | Network edges only |",
        "|---|---:|---:|---:|",
        f"| Nodes | {allm['nodes']} | {metrics['grade_a_only']['nodes']} | {net['nodes']} |",
        f"| Edges | {allm['edges']} | {metrics['grade_a_only']['edges']} | {net['edges']} |",
        f"| Unique person–entity pairs | {allm['unique_pairs']} | {metrics['grade_a_only']['unique_pairs']} | {net['unique_pairs']} |",
        f"| Largest component | {allm['components']['largest']} | {metrics['grade_a_only']['components']['largest']} | {net['components']['largest']} |",
        f"| Degree-1 nodes | {allm['degree']['degree_1']} | {metrics['grade_a_only']['degree']['degree_1']} | {net['degree']['degree_1']} |",
        "",
        "## Edges by class",
        "",
        "| Class | Edges |",
        "|---|---:|",
    ]
    for key, value in sorted(allm["edges_by_class"].items()):
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## Edges by evidence grade",
        "",
        "| Grade | Edges |",
        "|---|---:|",
    ]
    for key, value in sorted(allm["edges_by_grade"].items()):
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## Top hubs (all verified edges)",
        "",
        "| Entity | Kind | Degree |",
        "|---|---|---:|",
    ]
    for hub in allm["top_hubs"][:15]:
        lines.append(f"| {hub['name']} | {hub['kind']} | {hub['degree']} |")
    lines += [
        "",
        "## Top co-affiliations",
        "",
        "| Person A | Person B | Shared organisations |",
        "|---|---|---:|",
    ]
    for pair in metrics["co_affiliation"][:15]:
        lines.append(f"| {pair['a']} | {pair['b']} | {pair['shared_orgs']} |")
    lines += [
        "",
        "## Notes",
        "",
        "- `network` = membership, board, advisory, chair, founder, fellow, attendee.",
        "- `occupational` = employer and held position.",
        "- `education` = education and degree.",
        "- `institutional` = commission service.",
        "- Every edge carries `quote`, `doc_id`, `doc_title`, `doc_path`, and `doc_sha256`.",
        "- `source_url` is empty only for local-only documents (DG CVs, CJEU, declarations); the path and hash identify them.",
        f"- {metrics.get('excluded_quarantined_endpoints', 0)} verified claims are excluded because an endpoint is quarantined.",
        "",
    ]
    return "\n".join(lines)

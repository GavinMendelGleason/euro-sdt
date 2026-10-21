#!/usr/bin/env python3
"""Render a static overview of the verified graph.

Examples:
  python scripts/plot_graph.py
  python scripts/plot_graph.py --edge-class network --grades A --top 120
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

GRAPH_DIR = Path("graph")

PERSON_COLORS = {
    "commissioner": "#4C78A8",
    "mep": "#59A14F",
    "mep_sdt": "#59A14F",
    "dg": "#F28E2B",
    "ddg": "#F28E2B",
    "corporate_elite": "#E15759",
    "cjeu_judge": "#B07AA1",
    "cjeu_ag": "#B07AA1",
}
KIND_COLORS = {
    "organisation": "#BAB0AC",
    "institution": "#BAB0AC",
    "university": "#9C755F",
    "commission": "#111111",
}
GRADE_COLORS = {"A": "#4C78A8", "B": "#F28E2B", "C": "#E15759"}


def load(nodes_path: Path, edges_path: Path, edge_class: str | None, grades: set[str]):
    with nodes_path.open(newline="", encoding="utf-8") as fh:
        nodes = {row["id"]: row for row in csv.DictReader(fh)}
    edges = []
    with edges_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if edge_class and row["edge_class"] != edge_class:
                continue
            if grades and row["grade"] not in grades:
                continue
            if row["source"] not in nodes or row["target"] not in nodes:
                continue
            edges.append(row)
    return nodes, edges


def top_subgraph(nodes, edges, top: int):
    degree = Counter()
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    keep = {node_id for node_id, _ in degree.most_common(top)}
    kept_edges = [e for e in edges if e["source"] in keep and e["target"] in keep]
    # Only keep nodes that remain connected after the cut.
    degree = Counter()
    for edge in kept_edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    keep = {node_id for node_id in keep if degree[node_id] > 0}
    kept_edges = [e for e in kept_edges if e["source"] in keep and e["target"] in keep]
    return keep, kept_edges, degree


def spring_layout(count: int, edges: list[tuple[int, int]], iterations: int = 140, seed: int = 7):
    rng = np.random.default_rng(seed)
    pos = rng.normal(size=(count, 2))
    pos -= pos.mean(axis=0)
    pos /= np.abs(pos).max()
    k = np.sqrt(1.0 / max(1, count))
    for iteration in range(iterations):
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(delta, axis=2)
        np.fill_diagonal(dist, np.inf)
        disp = (delta / (dist[:, :, None] ** 2) * (k ** 2)).sum(axis=1)
        for a, b in edges:
            delta_ab = pos[a] - pos[b]
            length = np.linalg.norm(delta_ab) + 1e-9
            force = (length ** 2 / k) * delta_ab / length
            disp[a] -= force
            disp[b] += force
        temperature = 0.12 * (1 - iteration / iterations)
        norms = np.linalg.norm(disp, axis=1, keepdims=True)
        norms[norms == 0] = 1
        pos += disp / norms * np.minimum(norms, temperature)
    pos -= pos.mean(axis=0)
    pos /= np.abs(pos).max()
    return pos


def node_color(node: dict) -> str:
    if node["kind"] == "person":
        return PERSON_COLORS.get(node.get("category") or "", "#9C755F")
    return KIND_COLORS.get(node["kind"], "#BAB0AC")


def plot(nodes_path: Path, edges_path: Path, output: Path, edge_class: str | None,
         grades: set[str], top: int, labels: int):
    nodes, edges = load(nodes_path, edges_path, edge_class, grades)
    keep, edges, degree = top_subgraph(nodes, edges, top)
    order = sorted(keep, key=lambda node_id: (-degree[node_id], nodes[node_id]["name"]))
    index = {node_id: i for i, node_id in enumerate(order)}
    positions = spring_layout(len(order), [(index[e["source"]], index[e["target"]]) for e in edges], iterations=220)
    positions = positions * 10

    fig, ax = plt.subplots(figsize=(16, 11), facecolor="white")
    for edge in edges:
        a, b = index[edge["source"]], index[edge["target"]]
        ax.plot(
            [positions[a, 0], positions[b, 0]],
            [positions[a, 1], positions[b, 1]],
            color=GRADE_COLORS.get(edge["grade"], "#999999"),
            alpha=0.22 if edge["grade"] == "A" else 0.30,
            linewidth=0.5 if edge["grade"] == "A" else 0.8,
            zorder=1,
        )
    for node_id in order:
        node = nodes[node_id]
        i = index[node_id]
        size = 35 + min(450, degree[node_id] * 18)
        ax.scatter(
            positions[i, 0], positions[i, 1], s=size,
            c=node_color(node), edgecolors="white", linewidths=0.6,
            alpha=0.92, zorder=2,
        )
    for rank, node_id in enumerate(order[:labels]):
        node = nodes[node_id]
        i = index[node_id]
        above = rank % 2 == 0
        ax.text(
            positions[i, 0], positions[i, 1] + (0.22 if above else -0.22),
            node["name"], fontsize=7.2, ha="center",
            va="bottom" if above else "top",
            color="#222222", zorder=3,
        )

    ax.set_title(
        f"Verified elite graph — {edge_class or 'all edges'}, grades {'/'.join(sorted(grades)) or 'all'}, "
        f"top {len(order)} nodes by degree\n{len(order)} nodes · {len(edges)} edges · source: graph/edges.csv",
        fontsize=13, loc="left",
    )
    ax.set_axis_off()

    legend = [
        Patch(facecolor="#4C78A8", label="Commissioner"),
        Patch(facecolor="#59A14F", label="MEP"),
        Patch(facecolor="#F28E2B", label="DG / DDG"),
        Patch(facecolor="#E15759", label="Corporate elite"),
        Patch(facecolor="#B07AA1", label="CJEU"),
        Patch(facecolor="#BAB0AC", label="Organisation"),
        Patch(facecolor="#111111", label="Commission body"),
        Line2D([0], [0], color=GRADE_COLORS["A"], lw=1.2, label="Grade A edge"),
        Line2D([0], [0], color=GRADE_COLORS["B"], lw=1.2, label="Grade B edge"),
        Line2D([0], [0], color=GRADE_COLORS["C"], lw=1.2, label="Grade C edge"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=8, frameon=False)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight", facecolor="white")
    svg = output.with_suffix(".svg")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {output} and {svg} ({len(order)} nodes, {len(edges)} edges)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=Path, default=GRAPH_DIR / "nodes.csv")
    parser.add_argument("--edges", type=Path, default=GRAPH_DIR / "edges.csv")
    parser.add_argument("--output", type=Path, default=GRAPH_DIR / "graph_overview.png")
    parser.add_argument("--edge-class", default="network",
                        choices=["network", "occupational", "education", "institutional", "other", "all"])
    parser.add_argument("--grades", default="A,B")
    parser.add_argument("--top", type=int, default=140)
    parser.add_argument("--labels", type=int, default=24)
    args = parser.parse_args()
    edge_class = None if args.edge_class == "all" else args.edge_class
    grades = {g.strip() for g in args.grades.split(",") if g.strip()}
    plot(args.nodes, args.edges, args.output, edge_class, grades, args.top, args.labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

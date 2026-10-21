#!/usr/bin/env python3
"""Render graph, wiki and audit from euro_sdt_v2.db."""
from euro_sdt.v2.audit_v2 import audit
from euro_sdt.v2.db import connect
from euro_sdt.v2.graph import build_graph
from euro_sdt.v2.report import generate_report
from euro_sdt.v2.wiki import generate_wiki

if __name__ == "__main__":
    db = connect()
    metrics = build_graph(db)
    counts = generate_wiki(db)
    report = audit(db)
    generate_report(db)
    print("graph:", metrics["all_verified"]["nodes"], "nodes,", metrics["all_verified"]["edges"], "edges")
    print("wiki:", counts)
    print("assertions:", report["assertions_by_status"])

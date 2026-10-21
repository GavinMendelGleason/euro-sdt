#!/usr/bin/env python3
"""Reproduce the v1 evidence baseline."""
from euro_sdt.v2.audit_v1 import audit

if __name__ == "__main__":
    report = audit()
    print(f"wrote audit/v1_baseline.md ({report['total_provenance']} provenance rows)")

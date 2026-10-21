#!/usr/bin/env python3
"""Run LLM adjudication over non-A evidence."""
import argparse

from euro_sdt.v2.adjudicate import adjudicate
from euro_sdt.v2.db import connect

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--model", default=None)
    parser.add_argument("--thinking", action="store_true")
    args = parser.parse_args()
    print(adjudicate(connect(), limit=args.limit, workers=args.workers,
                     model=args.model, thinking=args.thinking))

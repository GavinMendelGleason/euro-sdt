# European Social Demographic Theory (ESDT)

Research into EU institutional elites — their recruitment, career patterns, education, and transatlantic
network affiliations — using LLM-assisted analysis with phrase-level provenance.

## Quick Start

```bash
# Regenerate the Obsidian wiki from the database
.venv/bin/python3 genwiki.py

# Run the citation cross-checker against the methodology paper
.venv/bin/python3 check_citations.py assets/papers/methodology/paper.tex
```

Open `wiki/` as an Obsidian vault to explore the knowledge graph.

## Evidence Standard

**Every fact must have provenance** — a specific sentence in a specific source document. LLMs are used as
extraction engines, not authorities: each extracted claim is cross-verified against source text at the
phrase level before it enters the database.

Acceptable sources: official EU documents, CVs published by institutions, Wikipedia articles, Wikidata
P69/P4100 queries, scraped institutional web pages. CSVs without documented provenance are never ingested.

See [`AGENTS.md`](AGENTS.md) for the full evidence methodology and pipeline documentation.

## Project Structure

| Path | Purpose |
|---|---|
| `euro_sdt.db` | SQLite database — single source of truth (~4,700 facts, ~2,000 entities) |
| `wiki/` | Obsidian vault — auto-generated entity pages with graph-view colouring |
| `genwiki.py` | Wiki generator with auto-education-clusters and org validation |
| `extract_orgs.py` | LLM org membership extraction (deepseek-v4-pro) |
| `edu_dedup.py` | Education institution deduplication with evidence verification |
| `validate_entities.py` | LLM entity validation (VALID/STRIP/INVALID per organisation) |
| `check_citations.py` | Paper citation cross-checker with hash cache |
| `sources/` | Raw source texts (Wikipedia bios, DG CV PDFs, CJEU bios) |
| `manifests/` | LLM extraction manifests with phrase-level provenance |
| `assets/papers/methodology/` | Workshop paper (LaTeX + PDF) |
| `AGENTS.md` | Contributor workflow and resource map |
| `WIKI.md` | Full data inventory — authoritative index of all datasets |
| `Entities.md` | Organisation research notes |
| `papers/BIBLIOGRAPHY.md` | Paper citation catalog |

## Pipeline

```
scrape → extract (LLM phrase-level manifest) → verify (cross-check) → resolve (dedup) → render (wiki)
```

All LLM operations use `deepseek-v4-pro` with `thinking: disabled`.

## Coverage

| Category | Education | Org Affiliations |
|---|---|---|
| Commissioners (7 terms, 1995–2029) | 95% | — |
| DGs/DDGs | 87% | 79% |
| MEPs (SDT subset, EP4–EP10) | 56% | 76% |
| Corporate elites (30 companies) | 67% | 87% |
| CJEU | 59% | 28% |

## Papers

- **Phrasal Provenance: An LLM-Assisted Methodology for Elite Network Research**
  (Gavin Mendel-Gleason & Donagh Davis, Workshop on AI Methodology for Social Science,
  May 2026) — [`assets/papers/methodology/paper.tex`](assets/papers/methodology/paper.tex)

## License

See [`LICENSE`](LICENSE).

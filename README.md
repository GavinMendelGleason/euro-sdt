# European Social Demographic Theory (ESDT)

Research into EU institutional elites — their recruitment, career patterns, education, and transatlantic
network affiliations — using LLM-assisted analysis with phrase-level provenance.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv venv
uv pip install -e ".[all]"
cp .env.example .env   # add your DEEPSEEK_API_KEY
```

## v2 assertion layer (current)

The v1 database and wiki are retained as a candidate pool and source corpus. The
evidence layer has been rebuilt as `euro_sdt_v2.db`:

- every claim points at a sentence ID in a hashed source document;
- every verified assertion has a located quote;
- evidence grades A/B/C are explicit, and LLM adjudication is recorded;
- the graph is exported as CSV/GraphML with edge class, role, quote, and source.

```bash
.venv/bin/python scripts/audit_v1.py                 # reproduce the v1 baseline
.venv/bin/python scripts/run_v2.py                   # rebuild v2 claims/evidence
.venv/bin/python scripts/extract_v2.py --categories commissioner  # full-document extraction
.venv/bin/python scripts/adjudicate.py --workers 6   # judge non-A evidence
.venv/bin/python scripts/render_v2.py                # graph + wiki + audit
.venv/bin/python scripts/check_v2.py                 # CI invariants
.venv/bin/python scripts/review.py list --include-a   # human review queue
.venv/bin/python scripts/recheck_grade_a.py --dry-run --limit 100  # grade-A second judge
```

Current build: **5,380 claims**, **4,036 verified**, 177 needs review, 1,167
rejected; **3,594 graph edges** (2,612 network, 525 education, 361
occupational, 94 institutional, 2 other). Every edge has a located quote and a
hashed source document; 119 edges point at local-only documents (DG CVs, CJEU,
declarations) with a path and SHA-256 but no public URL. 25 verified claims are
excluded because an endpoint is quarantined. A second judge rechecked all 738
grade-C claims: 569 kept, 169 moved to `needs_review`. See [`docs/v2-methodology.md`](docs/v2-methodology.md)
for the model, grading rules, and invariants. The v1 commands below remain for
the historical corpus and are not the source of the current graph.

## Pipeline

The pipeline has five stages. All LLM operations use `deepseek-v4-pro` with `thinking: disabled`.

### 1. Scrape — acquire source texts

```bash
euro-sdt scrape commission      # VdL II commissioner list → commission_2024_2029.csv
euro-sdt scrape meps            # MEP list → meps_2024_2029.csv
euro-sdt scrape cvs             # Wikidata CV data (P69/P4100) for MEPs & commissioners
euro-sdt scrape declarations    # Parse EC machine-readable declarations ZIP
euro-sdt scrape sources         # Extract plain text + phrase indices to sources/
```

### 2. Extract — LLM phrase-level fact extraction

```bash
euro-sdt extract orgs           # Organisation memberships with phrase provenance → manifests/
euro-sdt extract dedup-edu      # Education institution deduplication
euro-sdt extract validate       # LLM entity name validation (VALID/STRIP/INVALID)
```

### 3. Verify — cross-check facts against source text

```bash
euro-sdt extract verify         # LLM verification of every fact against its source quote
```

### 4. Resolve — deduplicate entities

```bash
euro-sdt extract dedup-edu      # Two-pass LLM dedup: auto-merge (similarity ≥ 0.95) + LLM judge
```

### 5. Render — generate output artifacts

```bash
euro-sdt render wiki            # Obsidian wiki → wiki/
euro-sdt render analytics       # Charts → wiki/img/
euro-sdt check-citations assets/papers/methodology/paper.tex  # Cross-check paper citations
euro-sdt status                 # DB coverage report
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
| `src/euro_sdt/` | Python package (scrape, extract, render, CLI, config, db) |
| `euro_sdt.db` | SQLite database — single source of truth (~4,700 facts, ~2,000 entities) |
| `wiki/` | Obsidian vault — auto-generated entity pages with graph-view colouring |
| `sources/` | Raw source texts (Wikipedia bios, DG CV PDFs, CJEU bios) |
| `manifests/` | LLM extraction manifests with phrase-level provenance |
| `assets/papers/methodology/` | Workshop paper (LaTeX + PDF) |
| `pyproject.toml` | Project metadata, dependencies, and entry points |
| `.env.example` | Template for `DEEPSEEK_API_KEY` |
| `AGENTS.md` | Contributor workflow and resource map |
| `WIKI.md` | Full data inventory — authoritative index of all datasets |
| `Entities.md` | Organisation research notes |
| `papers/` | Cited work PDFs + bibliography |

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

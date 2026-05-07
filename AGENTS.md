# AGENTS.md

## Rules

- NEVER disclose environment variables or secrets.
- Always commit and push completed work before ending a session (see Git Workflow below).
- Always pull from the remote before starting new work (see Git Workflow below).

## Evidence Standard

**Collected data is NOT proof.** Our CSVs, scraped pages, Wikidata queries, and database records are internal research tools — they do not themselves constitute evidence. Every factual claim must be traceable to an external, publicly accessible primary source that an independent researcher can verify.

Acceptable proof:
- **Official EU documents**: Commission declarations of interests (machine-readable ZIP), ethics committee decisions (published at commission.europa.eu), Eur-Lex legal texts
- **CVs and biographies published by the institution**: Commission person pages, CJEU member biographies, official institutional CV PDFs
- **Wikipedia articles**: Acceptable for biographical facts (birth year, education, career positions) that appear in the article text — but the Wikipedia page URL and specific sentence must be cited
- **Organisation websites**: For organisational classification facts (funding sources, mission, governance) — the specific page and paragraph must be cited
- **Scraped web pages**: Acceptable as primary source material when the scraped page is a well-regarded institutional or news source. The scraped text must be preserved as a source document.
- **Wikidata queries**: May be used as evidence where there is little risk of ambiguity or entity duplication (e.g., structured facts with unique QIDs). Should be verified against additional sources where possible.
- **Academic publications**: Peer-reviewed journal articles and academic books
- **News articles in major media**: Established outlets for event-based claims and appointments
- **Curriculum vitae**: Official CVs published by the individual or their institution

Not acceptable as proof:
- Our own CSVs, JSON files, or database records
- Inferences or keyword matches that cannot be pinned to a specific sentence in a source document
- Data derived from other datasets without a traceable source chain

**Every fact in the database must have a provenance record linking it to a specific source document and (ideally) a specific sentence.** Facts without this are flagged as `unproven` and should not be used in analysis or publication.

---

## Paper Citation Standard

**No paper may cite any reference unless:**
1. A PDF of the cited work exists locally in `papers/`
2. The PDF has been cross-checked by `check_citations.py` — a script that extracts the citing claim from the paper, searches the PDF text for supporting evidence, and logs the verification

Note: `assets/papers/` is for *our* papers (the ones we are writing). `papers/` is for PDFs of works we *cite*.

### `check_citations.py`

Reads a LaTeX file, finds all `\footnote{}` and `\cite{}` commands, locates the corresponding PDF in `papers/`, extracts text from the PDF, and verifies that the claim each citation supports is actually substantiated by the cited work. Outputs a verification report.

Usage:
```bash
.venv/bin/python check_citations.py assets/papers/methodology/paper.tex
```

Produces `verification_report.csv` with columns: `paper_section, claim, citation, pdf_file, evidence_found, confidence`.

**After adding or modifying any citation, run `check_citations.py` before committing.** The checker uses LLM-powered phrase-level verification with confidence scoring (1-5 scale). All citations must achieve confidence ≥ 3 before submission.

The paper bibliography is maintained in `papers/BIBLIOGRAPHY.md` — all cited works must be cataloged there with verification status.

---

## Data Methodology

All data follows a five-stage pipeline derived from the methodology described in `assets/papers/methodology/paper.tex`:

### 1. Scrape
Acquire source texts from controlled, publicly accessible sources. Never use proprietary datasets or unverified CSVs as primary evidence. Sources include:
- **Wikipedia** — commissioner/MEP/corporate biographies via API extracts and raw HTML
- **Commission CVs** — DG/DDG CV PDFs from the EU Person Directory, converted to plaintext
- **Wikidata** — SPARQL queries for P39 (position), P69 (education), P1416 (affiliation) for entity discovery only (not as fact source)
- **Official documents** — machine-readable declarations of interests, EP hearing transcripts

Source files are saved to `sources/{wikipedia,dg_cvs,cjeu}/` with phrase indices (`*.phrases` files).

### 2. Extract (Phrase-Level Manifest)
Send the source text to an LLM (DeepSeek) with numbered phrases. The LLM returns a JSON **manifest** — a structured extraction specifying:
- `phrase`: the phrase number where evidence appears
- `organisation` / `institution`: the entity name exactly as written
- `role`: relationship (member, board member, fellow, etc.)
- `reasoning`: one sentence explaining why the phrase indicates the fact

The manifest is stored as a durable intermediate artifact in `manifests/`. Facts are NEVER extracted from CSVs or inferred — every claim traces to a specific sentence in a source document.

### 3. Verify (Cross-Check)
Each extracted fact is validated against the source text at the claimed phrase index. If the sentence does not contain the asserted information, the fact is rejected. Phrase-index cross-checking catches hallucinations (e.g., the LLM returning "Dacian Julien Cioloș" as an institution name — the commissioner's own name).

### 4. Resolve (Entity Dedup)
Organisation and institution names are deduplicated using a two-pass approach:
- **Auto-merge**: string similarity ≥ 0.95 (typos, punctuation variants)
- **LLM judge**: borderline pairs (0.30–0.95) sent to LLM with up to 3 evidence phrases from each side. LLM returns SAME/DIFFERENT with reasoning. All decisions logged in `_dedup.json`.

### 5. Render (Wiki + DB)
Facts are loaded into `euro_sdt.db` with mandatory provenance (`citation_id`, `phrase_index`, `quote_text`). `genwiki.py` generates the Obsidian wiki with citation footnotes. Facts without provenance are deleted.

### Key Principles
- **Every fact must have provenance** — a specific sentence in a specific source document
- **Collected data is NOT proof** — CSVs, scraped pages, and DB records are internal tools, not evidence
- **LLM is an extraction engine, not an authority** — it generates hypotheses verified against source text
- **Manifests are the durable intermediate artifact** — database rows can be rebuilt from manifests

---

## Git Workflow

This repository is shared between multiple contributors (Gavin and Donagh). To avoid conflicts and data loss:

**At the start of every session:**
```bash
cd /home/<user>/dev/Personal/euro-sdt
git pull origin main
```

**After completing any meaningful unit of work:**
```bash
git add <files>
git commit -m "Descriptive message explaining what was done and why"
git push
```

**If a push is rejected (someone else pushed first):**
```bash
git pull --rebase
git push
```

Make commits frequently — after each new dataset, script, or analysis step. Do not accumulate uncommitted work across multiple tasks.

---

## Resource Map

All data files live in the repository root. The authoritative index is **`WIKI.md`**, which documents every dataset with its source, record count, fields, and generating script.

### Data files by category

**European Commission — member lists**
| File | Commission | Records |
|---|---|---|
| `commission_santer_1995_1999.csv` | Santer (1995–99) | 20 |
| `commission_prodi_1999_2004.csv` | Prodi (1999–04) | 21 |
| `commission_barroso_i_2004_2009.csv` | Barroso I (2004–09) | 30 |
| `commission_barroso_ii_2010_2014.csv` | Barroso II (2010–14) | 28 |
| `commission_juncker_2014_2019.csv` | Juncker (2014–19) | 28 |
| `commission_i_2019_2024.csv` | VdL I (2019–24) | 30 |
| `commission_2024_2029.csv` | VdL II (2024–29) | 27 |

**European Commission — Wikidata CVs**
| File | Commission |
|---|---|
| `commission_santer_1995_1999_cv_data.csv` | Santer |
| `commission_prodi_1999_2004_cv_data.csv` | Prodi |
| `commission_barroso_i_2004_2009_cv_data.csv` | Barroso I |
| `commission_barroso_ii_2010_2014_cv_data.csv` | Barroso II |
| `commission_juncker_cv_data.csv` | Juncker |
| `commission_i_cv_data.csv` | VdL I |
| `commission_cv_data.csv` | VdL II |

**European Commission — other datasets**
| File | Contents |
|---|---|
| `commission_affiliations.csv` | VdL II Declarations of Interests (344 entries) |
| `commission_revolving_door.csv` | Post-mandate occupation decisions, all commissions |
| `commissioner_education_by_country.csv` | Education clusters + elite institution flags, all commissions |
| `commissioner_education_enriched.csv` | Wikidata + Wikipedia education keyword search |
| `commissioner_education.csv` | Raw Wikidata P69 education entries |
| `commissioner_appointments.csv` | Prior roles + education + Atlanticist ties combined |
| `commissioner_trends_by_commission.csv` | Key metrics by commission term (elite uni %, Atlanticist %, etc.) |

**Organisation affiliations**
| Path | Contents |
|---|---|
| `manifests/` | Phrase-level LLM extraction manifests — 150 commissioner org membership extractions with sentence provenance. `_index.json` and `_dedup.json` provide overview + entity resolution mapping. Generated by `extract_orgs.py` |
| `organisations_classified.csv` | 38 orgs — type, atlanticist/NATO/US flags, description (flags unverified, org names are reference only) |

**EP confirmation hearing documents (VdL I, 2019)**
| Path | Contents |
|---|---|
| `ep_hearings_2019/` | 22 PDFs — questionnaires, transcripts, further written Qs |

**MEPs**
| File | Contents |
|---|---|
| `meps_2024_2029.csv` | 734 MEPs, 10th Parliament |
| `mep_cv_data.csv` | Wikidata CVs for MEPs |

**Court of Justice (CJEU)**
| File | Contents |
|---|---|
| `cjeu_members_list.csv` | 39 members (27 judges + 12 AGs), Wikidata QIDs |
| `cjeu_cv_data.csv` | Wikidata CVs + CJEU page memberships |
| `cjeu_bios_full.json` | Full biography text for 10 members from CJEU website |

**Machine-readable declarations ZIP**
| File | Contents |
|---|---|
| `Machine-Readable-DOIs.zip` | VdL II official declarations ZIP (April 2026) |

### Scripts

| Script | Purpose |
|---|---|
| `scrape_meps.py` | Scrape MEP list from Wikipedia |
| `scrape_cvs.py` | Wikidata CVs for MEPs |
| `scrape_commission.py` | Scrape VdL II commissioner list from Wikipedia |
| `scrape_commission_cvs.py` | Wikidata CVs for VdL II |
| `scrape_commission_i_cvs.py` | Wikidata CVs for VdL I |
| `scrape_commission_juncker_cvs.py` | Wikidata CVs for Juncker |
| `scrape_barroso_ii_2010_2014_cvs.py` | Wikidata CVs for Barroso II |
| `scrape_barroso_i_2004_2009_cvs.py` | Wikidata CVs for Barroso I |
| `scrape_santer_1995_1999_cvs.py` | Wikidata CVs for Santer |
| `scrape_prodi_1999_2004_cvs.py` | Wikidata CVs for Prodi |
| `parse_declarations.py` | Parse EC machine-readable declarations ZIP (OOXML) |
| `extract_orgs.py` | Phrase-level LLM org membership extraction → manifests/ + DB facts |

---

## Entity Tracking

Organisations appearing in the data are researched and classified in two places:

### `organisations_classified.csv`
Machine-readable classification of every organisation encountered. Fields:
- `organisation` — canonical name
- `type` — e.g. "Think tank", "Elite network", "NGO"
- `atlanticist` — TRUE/FALSE
- `nato_adjacent` — TRUE/FALSE
- `us_linked` — TRUE/FALSE
- `funding_notes` — primary funding sources
- `headquarters` — city, country
- `description` — summary description

**To add a new organisation:** append a row to `organisations_classified.csv` following the existing format, then add a full entry to `Entities.md`.

### `Entities.md`
Detailed research notes for each organisation — governance, funding, staff, commissioner connections, and the evidentiary basis for the Atlanticist classification. Currently documents 13 organisations:

- Friends of Europe
- Atlantic Council
- Munich Security Conference
- World Economic Forum
- ECFR
- GLOBSEC
- European Leadership Network
- IRI / NED
- RAND Europe
- Elcano Royal Institute *(reclassified as non-Atlanticist April 2026)*
- Wilfried Martens Centre
- Bilderberg Group *(in organisations_classified.csv, not yet in Entities.md)*
- Trilateral Commission *(in organisations_classified.csv, not yet in Entities.md)*

**To research a new organisation:**
1. Fetch primary sources (org website, EU Transparency Register, annual reports)
2. Document governance, funding, commissioner connections, and Atlanticist assessment in `Entities.md`
3. Update `organisations_classified.csv` with the classification flags
4. Update the index table at the top of `Entities.md`
5. Commit and push

---

## Adding New Data

When adding a new dataset:
1. Save the CSV/JSON to the repository root
2. Add an entry to the **Data Inventory** section of `WIKI.md` (source, record count, fields, scraper)
3. If it introduces new organisations, classify them in `organisations_classified.csv` and `Entities.md`
4. Commit and push with a descriptive message

---

## Key Reference Files

| File | Purpose |
|---|---|
| `WIKI.md` | Full data inventory — authoritative index of all datasets |
| `Entities.md` | Organisation research notes |
| `organisations_classified.csv` | Machine-readable org classification |
| `manifests/` | LLM extraction manifests (org memberships, with phrase-level provenance) |
| `commissioner_trends_by_commission.csv` | Key metrics by commission term |
| `papers/BIBLIOGRAPHY.md` | Paper citation catalog with PDF availability and verification status |
| `check_citations.py` | Cross-checks paper citations against local PDFs |
| `assets/papers/` | Our papers (LaTeX source + compiled PDFs) |
| `AGENTS.md` | This file — workflow and resource map for agents/contributors |

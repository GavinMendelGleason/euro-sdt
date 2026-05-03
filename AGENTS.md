# AGENTS.md

## Rules

- NEVER disclose environment variables or secrets.
- Always commit and push completed work before ending a session (see Git Workflow below).
- Always pull from the remote before starting new work (see Git Workflow below).

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

**Atlanticist network analysis**
| File | Contents |
|---|---|
| `organisations_classified.csv` | 34 orgs — type, atlanticist/NATO/US flags, description |
| `atlanticist_comparison.csv` | Seven-commission comparison table (18 orgs × 7 commissions) |
| `atlanticist_org_hits.csv` | VdL II declaration-based Atlanticist hits |
| `commission_i_atlanticist_hits.csv` | VdL I Wikipedia-based hits |
| `barroso_atlanticist_hits.json` | Barroso I + II Wikipedia-based hits |
| `santer_prodi_atlanticist_hits.json` | Santer + Prodi Wikipedia-based hits |
| `vdl1_extended_atlanticist_hits.json` | VdL I extended keyword search results |

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
| `atlanticist_comparison.csv` | Cross-commission Atlanticist network table |
| `commissioner_trends_by_commission.csv` | Key metrics by commission term |
| `AGENTS.md` | This file — workflow and resource map for agents/contributors |

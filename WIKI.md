# European Social Demographic Theory (ESDT) — WIKI

Research into European political elites, their recruitment, career patterns, and transatlantic networks.

---

## Data Inventory

### 1. Members of the European Parliament (2024–2029)
**File:** `meps_2024_2029.csv`
**Source:** Scraped from Wikipedia (10th European Parliament)
**Records:** 734 MEPs across 27 member states

| Group | Seats |
|---|---|
| EPP (European People's Party) | 192 |
| S&D (Socialists & Democrats) | 139 |
| Patriots for Europe | 90 |
| Renew Europe | 78 |
| ECR (Conservatives & Reformists) | 78 |
| Greens/EFA | 53 |
| The Left | 46 |
| Non-Inscrits | 32 |
| Europe of Sovereign Nations | 26 |

**Top countries by seats:** Germany (96), France (84), Italy (77), Spain (61), Poland (53)
**Scraper:** `scrape_meps.py`

---

### 2. MEP CV Data (2024–2029)
**File:** `mep_cv_data.csv`
**Source:** Wikidata SPARQL (P69 education, P106 occupations, P108 employers, P102 party, P166 awards, P39 positions)
**Records:** 734 MEPs
**Scraper:** `scrape_cvs.py`

---

### 3. European Commission — Von der Leyen II (2024–2029)
**File:** `commission_2024_2029.csv`
**Source:** Scraped from Wikipedia (Von der Leyen Commission II page)
**Records:** 27 commissioners
**Fields:** Name, Portfolio, Country, National\_Party, EP\_Group, Directorate\_General
**Scraper:** `scrape_commission.py`

---

### 4. Commission II CV Data (2024–2029)
**File:** `commission_cv_data.csv`
**Source:** Wikidata SPARQL
**Records:** 25/27 commissioners matched
**Fields:** education, occupations, employers, party\_history, awards, prev\_positions, birth\_date, birth\_place
**Scraper:** `scrape_commission_cvs.py`

---

### 5. Commission II Declarations of Interests (2024–2029)
**File:** `commission_affiliations.csv`
**Source:** EC machine-readable ZIP (April 2026) — `commission.europa.eu/publications/declarations-interests-commissioners-machine-readable-format_en`
**Records:** 344 affiliation entries across 27 commissioners
**Fields:** commissioner, section, role, organisation, description
**Sections covered:** I.1 Foundations, I.2 Educational bodies, I.3 Governing/advisory organs, I.4 Other activities, II.1 Honorary posts, II.2 Other current functions
**Parser:** `parse_declarations.py`

---

### 6. European Commission — Von der Leyen I (2019–2024)
**File:** `commission_i_2019_2024.csv`
**Source:** commissioners.ec.europa.eu archive + manual portfolio mapping
**Records:** 30 commissioners (including mid-term replacements)
**Fields:** Name, Portfolio
**Note:** Declarations of Interests removed from EC servers on transition to Commission II; not recoverable.

---

### 7. Commission I CV Data (2019–2024)
**File:** `commission_i_cv_data.csv`
**Source:** Wikidata SPARQL
**Records:** 27/30 commissioners matched
**Fields:** education, occupations, employers, party\_history, awards, prev\_positions, birth\_date, birth\_place
**Coverage:** education 27/27, occupations 27/27, prev\_positions 27/27, employers 7/27
**Scraper:** `scrape_commission_i_cvs.py`

---

### 8. EP Confirmation Hearing Documents (2019)
**Directory:** `ep_hearings_2019/`
**Source:** European Parliament library (europarl.europa.eu/resources/library/media/)
**Records:** 22 PDFs covering ~12 commissioners
**Types:** Questionnaire responses (8), hearing transcripts (8), further written questions (1)
**Commissioners covered (EN docs):** Vestager, Goulard, Schinas, Sinkevičius, Gentiloni, Gabriel, Hogan, Šefčovič, Urpilainen, Schmit, Johansson, Hahn
**Note:** Questionnaires reference declarations but do not reproduce structured affiliation data.

---

### 9. Revolving Door Decisions (all commissions)
**File:** `commission_revolving_door.csv`
**Source:** EC ethics page — `commission.europa.eu/about/service-standards-and-principles/ethics-and-good-administration/commissioners-and-ethics/former-european-commissioners-authorised-occupations_en`
**Records:** 194 approved post-mandate occupation decisions
**Fields:** date, year, decision, name, mandate, occupation, sector, commission
**Coverage:**

| Commission | Decisions | Individuals |
|---|---|---|
| Von der Leyen I (2019–2024) | 32 | 15 |
| Juncker (2014–2019) | 90 | 26 |
| Barroso II / earlier | 72 | 26 |

**Sector classification:** Finance/corporate, Consultancy/lobbying, Think tank/advisory, Academia, NGO/foundation, Int'l organisation, Public/political

---

### 10. Organisations Classification
**File:** `organisations_classified.csv`
**Source:** Manually researched — official websites, funding disclosures, academic literature
**Records:** 34 organisations
**Fields:** organisation, type, atlanticist, nato\_adjacent, us\_linked, funding\_notes, headquarters, description
**Purpose:** Reference taxonomy for classifying affiliations found across all datasets

---

### 11. Atlanticist Org Hits — Commission II
**File:** `atlanticist_org_hits.csv`
**Source:** Cross-reference of `commission_affiliations.csv` against `organisations_classified.csv`
**Records:** 13 organisations with at least one commissioner connection
**Method:** Keyword search across all declaration text fields (role, organisation, description)

---

### 12. Atlanticist Org Hits — Commission I
**File:** `commission_i_atlanticist_hits.csv`
**Source:** Cross-reference of Wikidata CVs + Wikipedia article text against `organisations_classified.csv`
**Records:** 4 organisations (Wikipedia text search; likely undercount vs declarations)

---

### 13. Barroso I Commission (2004–2009)
**Files:** `commission_barroso_i_2004_2009.csv`, `commission_barroso_i_2004_2009_cv_data.csv`
**Source:** Commissioner list — manually compiled; CVs — Wikidata SPARQL
**Records:** 30 commissioners; 27/30 matched on Wikidata
**CV coverage:** education 25/27, occupations 27/27, prev\_positions 26/27
**Scraper:** `scrape_barroso_i_2004_2009_cvs.py`
**Note:** No declarations exist. Atlanticist analysis based on Wikipedia text search only.

---

### 14. Barroso II Commission (2010–2014)
**Files:** `commission_barroso_ii_2010_2014.csv`, `commission_barroso_ii_2010_2014_cv_data.csv`
**Source:** Commissioner list — manually compiled; CVs — Wikidata SPARQL
**Records:** 28 commissioners; 26/28 matched on Wikidata
**CV coverage:** education 26/26, occupations 26/26, prev\_positions 26/26
**Scraper:** `scrape_barroso_ii_2010_2014_cvs.py`
**Note:** No declarations exist. Atlanticist analysis based on Wikipedia text search only.

---

### 15. Juncker Commission (2014–2019)
**Files:** `commission_juncker_2014_2019.csv`, `commission_juncker_cv_data.csv`
**Source:** Commissioner list — manually compiled from official record; CVs — Wikidata SPARQL
**Records:** 28 commissioners; 27/28 matched on Wikidata
**CV coverage:** education 27/27, occupations 27/27, prev\_positions 26/27
**Scraper:** `scrape_commission_juncker_cvs.py`
**Note:** No machine-readable declarations exist — the structured XML format was introduced in 2018, after the Juncker mandate. Atlanticist analysis based on Wikipedia text search only.

---

### 16. Atlanticist Network Cross-Commission Comparison
**File:** `atlanticist_comparison.csv`
**Source:** Wikipedia biography text search + Wikidata (all commissions); additionally self-declarations for VdL II
**Records:** 19 rows (18 organisations + totals row)
**Fields:** Organisation, barroso\_i\_n/pct/commissioners, barroso\_ii\_n/pct/commissioners, juncker\_n/pct/commissioners, vdl\_i\_n/pct/commissioners, vdl\_ii\_n/pct/commissioners

**Summary table:**

| Organisation | Barr I n | Barr I % | Barr II n | Barr II % | Juncker n | Juncker % | VdL I n | VdL I % | VdL II n | VdL II % |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Council on Foreign Relations | 5 | 16.7% | 6 | 21.4% | 6 | 21.4% | 1 | 3.3% | — | — |
| Friends of Europe | 1 | 3.3% | 5 | 17.9% | 3 | 10.7% | 1 | 3.3% | 7 | 25.9% |
| ECFR | 4 | 13.3% | 5 | 17.9% | 4 | 14.3% | 2 | 6.7% | 1 | 3.7% |
| World Economic Forum / Davos | 1 | 3.3% | 2 | 7.1% | 1 | 3.6% | 2 | 6.7% | 3 | 11.1% |
| Bilderberg | 3 | 10.0% | 2 | 7.1% | 1 | 3.6% | — | — | — | — |
| Atlantic Council | — | — | 1 | 3.6% | 1 | 3.6% | — | — | 2 | 7.4% |
| GLOBSEC | — | — | 1 | 3.6% | 1 | 3.6% | 1 | 3.3% | 1 | 3.7% |
| Trilateral Commission | 1 | 3.3% | 2 | 7.1% | 1 | 3.6% | — | — | — | — |
| Marshall Fund (GMF) | — | — | 1 | 3.6% | 2 | 7.1% | — | — | — | — |
| Munich Security Conference | — | — | — | — | 1 | 3.6% | 1 | 3.3% | 1 | 3.7% |
| NATO (advisory/non-state role) | 1 | 3.3% | — | — | 2 | 7.1% | — | — | — | — |
| European Leadership Network | — | — | — | — | 1 | 3.6% | 1 | 3.3% | 1 | 3.7% |
| Aspen Institute | 1 | 3.3% | — | — | — | — | — | — | — | — |
| Atlantic Council of Finland | — | — | — | — | — | — | — | — | 1 | 3.7% |
| Elcano Royal Institute | — | — | — | — | — | — | — | — | 1 | 3.7% |
| IRI / NED | — | — | — | — | — | — | — | — | 1 | 3.7% |
| RAND Europe | — | — | — | — | — | — | — | — | 1 | 3.7% |
| Slovak Atlantic Commission | — | — | — | — | — | — | — | — | 1 | 3.7% |
| **TOTAL (unique)** | **11** | **36.7%** | **11** | **39.3%** | **10** | **35.7%** | **7** | **23.3%** | **16** | **59.3%** |

**Most connected individuals across all commissions:**
- Cecilia Malmström (10 org-hits): ECFR, Friends of Europe, Council on Foreign Relations, Trilateral Commission, Marshall Fund
- Kristalina Georgieva (8): Atlantic Council, ECFR, Council on Foreign Relations, WEF
- Joaquín Almunia (7): ECFR, Council on Foreign Relations, Friends of Europe
- Federica Mogherini (6): NATO PA, Friends of Europe, Munich Security Conference, ELN, Marshall Fund

**Methodological note:** All five commissions use Wikipedia biography text as the primary source — the only consistent cross-commission data available. VdL II additionally benefits from legally required self-declarations (the structured XML format was introduced in 2018), making its figures structurally more complete. All totals are likely undercounts relative to a declarations-based baseline, with VdL I being most affected by this gap.

---

## Scripts

| Script | Purpose | Output |
|---|---|---|
| `scrape_meps.py` | Scrape MEP list from Wikipedia | `meps_2024_2029.csv` |
| `scrape_cvs.py` | Wikidata CVs for MEPs | `mep_cv_data.csv` |
| `scrape_commission.py` | Scrape Commission II list from Wikipedia | `commission_2024_2029.csv` |
| `scrape_commission_cvs.py` | Wikidata CVs for Commission II | `commission_cv_data.csv` |
| `scrape_commission_i_cvs.py` | Wikidata CVs for Commission I | `commission_i_cv_data.csv` |
| `scrape_commission_juncker_cvs.py` | Wikidata CVs for Juncker Commission | `commission_juncker_cv_data.csv` |
| `scrape_barroso_ii_2010_2014_cvs.py` | Wikidata CVs for Barroso II | `commission_barroso_ii_2010_2014_cv_data.csv` |
| `scrape_barroso_i_2004_2009_cvs.py` | Wikidata CVs for Barroso I | `commission_barroso_i_2004_2009_cv_data.csv` |
| `parse_declarations.py` | Parse EC machine-readable DOI ZIP | `commission_affiliations.csv` |

**Dependencies:** `pandas`, `beautifulsoup4`, `lxml`, `pypdf` — install via `.venv/bin/pip install -r requirements.txt` (or manually)

---

## Research Agenda (`TODO.md`)

### Scoping
- Define "European Leadership" — heads of state, ministers, EU officials, MEPs, technocrats

### Data Collection
- Build database of European ministers/officials over time
- Collect CVs of European leadership

### Analysis Questions
- Entry barriers to European leadership
- Revolving doors: pre- and post-ministerial positions
- Atlanticist organisations in CVs (Bilderberg, Atlantic Council, ECFR, etc.)
- Evidence of increasing US influence in CV data over time

---

## Academic Papers (`papers/BIBLIOGRAPHY.md`)

1. **Political / Representative Elites** — EURELITE / EurElite network (9 entries)
2. **Ministerial Careers & Selection** — cabinet recruitment patterns (8 entries)
3. **EU / Transnational Elites** — IntUne survey data (3 entries)
4. **Revolving Doors** — post-cabinet career movements (9 entries)
5. **Corporate Elites / Interlocks** — interlocking directorate networks (3 entries)
6. **Power Elite / Social Immobility** — comparative elite analysis (2 entries)
7. **Atlanticist & Transatlantic Elite Networks** — Bilderberg Group (10 entries)
8. **Methods / Elite Research** — surveys and experiments (1 entry)

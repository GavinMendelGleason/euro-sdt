# European Social Demographic Theory (ESDT) — WIKI

Research into European political elites, their recruitment, career patterns, and transatlantic networks.

---

## Data Inventory

### 1. Members of the European Parliament (2024–2029)
**File:** `meps_2024_2029.csv`  
**Source:** Scraped from Wikipedia (10th European Parliament)  
**Records:** 734 MEPs across 27 member states  

**EP Group breakdown:**

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

**Scraper:** `scrape_meps.py` — fetches current MEP data from Wikipedia and writes to CSV.

---

### 2. Academic Papers
**Directory:** `papers/`  
**Bibliography:** `papers/BIBLIOGRAPHY.md` — annotated reading list with links and DOI references.

| Paper | Topic |
|---|---|
| ESF EURELITE Progress Report | European political elites convergence |
| Best et al. — *The Europe of Elites* | Elite composition across Europe |
| Carboni et al. (2024) | Social immobility of the European power elite |
| Heemskerk et al. (2013) | European corporate interlocking directorates |
| Fligstein (2008) — *Euroclash* | EU, European identity, and political conflict |
| Gijswijt (2024) | Bilderberg Group and Cold War Atlanticism |
| Kantor (2022) | Bilderberg Group PhD dissertation |
| Kertzer & Renshon (2022) | Experiments and surveys on political elites |

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

## Bibliography Topics (`papers/BIBLIOGRAPHY.md`)

1. **Political / Representative Elites** — EURELITE / EurElite network (9 entries)
2. **Ministerial Careers & Selection** — cabinet recruitment patterns (8 entries)
3. **EU / Transnational Elites** — IntUne survey data (3 entries)
4. **Revolving Doors** — post-cabinet career movements (9 entries)
5. **Corporate Elites / Interlocks** — interlocking directorate networks (3 entries)
6. **Power Elite / Social Immobility** — comparative elite analysis (2 entries)
7. **Atlanticist & Transatlantic Elite Networks** — Bilderberg Group (10 entries)
8. **Methods / Elite Research** — surveys and experiments (1 entry)

---

## Tools

- `scrape_meps.py` — Python scraper for Wikipedia MEP data (requires `pandas`, `beautifulsoup4`, `lxml`)

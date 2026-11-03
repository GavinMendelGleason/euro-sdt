# Data probe recovery

Recovered after the interrupted probe run. All probe artifacts are under `data/probes/`; source snapshots under `sources/official/probes/`.

## Probe inventory

| Probe | Rows | Key result |
|---|---:|---|
| `ask_eu.csv` | 24 | Article 255 2010–2022: 243 opinions; 130 first-term, 113 renewals; 92 seats in 2022 |
| `c255_post2022.csv` | 15 | 2023–2025 annual counts **not public**; eighth report in progress; fourth panel 70 opinions, 33 first-term / 37 renewals derived, not published |
| `national_cjeu_a.csv` | 15 | Only Portugal published a shortlist (3 names); most states publish only nominees |
| `national_cjeu_b.csv` | 47 | Sweden EGC: 9 applicants / 3 shortlisted; Poland: 6 CJ + 7 EGC admissible; Lithuania EGC: 4 applicants / 3 shortlisted |
| `national_cjeu_c.csv` | 22 | Croatia/Slovenia ran public calls; Bulgaria 2026 GC: 17 applications / 13 interviewed / 2 ranked (outside window) |
| `commission_pool.csv` | 32 | 27 Commissioner seats / 27 formal nominees; DG/DDG applicant counts **not public**; EPSO aggregate laureate data |
| `college_graduates.csv` | 24 | No annual graduate counts; enrolment series and completion rates only; 2024–25 bounded at 446–496 |
| `corporate_pool.csv` | 420 | 10 companies, 2019–2025; board seats/change data; AGM nominee lists, not applicant pools |
| `eligible_judicial_pool.csv` | 108 | 27 member states × 4 measures; 50 found, 11 partial, 17 not public, 3 blocked, 27 not applicable |

## Key candidate-pool findings

- **CJEU formal pool:** 243 opinions 2010–2022, 130 first-term and 113 renewals.
- **National CJEU pools:** only a handful publish applicant counts or shortlists; most publish the final nominee only.
- **Commission:** formal College nominees are public; management applicant pools are not.
- **Corporate:** AGM nomination lists are public, but applicant/candidate pools are not.
- **College of Europe:** enrolment and completion are public; annual graduates are not.

## Data gaps now confirmed

Not merely missing from our collection:

- 2023–2025 Article 255 annual counts.
- DG/DDG applicant pools.
- Corporate board applicant pools.
- College of Europe annual graduate counts.
- Most national CJEU applicant pools.

## Recoverable gaps

- National CJEU shortlists/applicant counts where published: SE, PL, LT, PT.
- Wider eligible judicial pool: partially built in `eligible_judicial_pool.csv`.
- Commission formal nominee count: 27/27.
- Corporate board turnover/seat data: 10 companies.

## File integrity

Some corporate `source_file` cells contain multiple source paths separated by `;`. The individual files exist under `sources/official/probes/`; a naive single-path existence check flags them as missing. This is a formatting issue, not lost provenance.

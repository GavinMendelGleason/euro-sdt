# batch_b: unavailable programme-level cohort data

Institutions in this batch: Harvard (Law School LL.M.), University of Oxford (Faculty of Law taught master's), University of Cambridge (Faculty of Law LL.M.), London School of Economics (Law School LL.M.).

`batch_b.csv` contains only figures printed explicitly in official institutional publications. Everything below was checked against the institutions' own pages and reports and either is not published at programme level or is published only as a range/approximation, which was not converted into an annual integer.

## University of Cambridge — LL.M.

No annual, programme-level series of applicants, admissions, enrolment or graduates for the Cambridge LL.M. was found.

- The University's *Postgraduate Admissions Statistics* reports (`sources/official/institutions/cambridge-pg-admissions-2019-20.txt`, `...-2022-23.txt`) aggregate to **Faculty of Law** level for all postgraduate law courses (LL.M., MCL, PhD and others) and, from 2020/21, only to degree type/school. Neither gives an LL.M.-only application, offer, confirmation or graduate count. Faculty-level totals are therefore not used: they are not the LL.M. cohort.
- The Faculty of Law LL.M. admissions pages (https://llm.law.cam.ac.uk/admissions/how-apply) give only rounded prospective figures for the 2027-28 cycle: "Number of available places: c. 190" and "Number of applicants: c. 1500". These are approximations for a cycle outside 2019-2025 and are not published as exact annual values, so no row is written.
- No official Cambridge LL.M. graduate count by year was located.

## Harvard Law School — LL.M.

- **Applicants and admitted**: not published. HLS publishes the J.D. 1L profile and the ABA Standard 509 report (J.D. only); neither covers LL.M. applications or offers.
- **Graduates**: taken from the Harvard Fact Book table *Degrees Conferred by School and Degree: AY2016-25*, https://oira.harvard.edu/factbook/fact-book-degrees (PDF: https://oira.harvard.edu/files/2025/12/completions_by_degree_251210.pdf). The LL.M. row gives degrees conferred per academic year, matched to the year in which that cohort entered (e.g. AY2019-20 degrees belong to the 2019 entry).
- **Enrolment 2020**: the size of the LL.M. class entering in 2020 was not published. HLS states only that 33 members of the 2020-21 class returned in 2021-22 to complete in person (https://hls.harvard.edu/today/a-new-academic-year-begins-one-step-at-a-time). Enrolment for 2020 is therefore blank; the 59 LL.M. degrees conferred in AY2020-21 are recorded as graduates with a note.
- **Graduates 2025**: AY2025-26 degree conferrals were not yet published at retrieval (2 Nov 2026).

## University of Oxford — BCL and MJur

Oxford has no LL.M.; its Faculty of Law taught master's degrees are the BCL and the MJur, recorded separately in `batch_b.csv`.

- **Applicants and admitted**: not published at programme level. The University's *Graduate Admissions Statistics* (https://www.ox.ac.uk/about/the-university/facts-and-figures/admissions-statistics/graduate, annual PDFs from 2019-20 to 2024-25) reports only **department/faculty** totals. For 2024-25 entry the Law row is: research 664 applications / 135 offers / 78 acceptances; taught 2,172 applications / 522 offers / 382 acceptances. That taught total covers the BCL, MJur, MSc in Law and Finance, MSc/MPhil in Criminology and other law courses, so it is not attributable to the BCL or MJur and is not used.
- **Enrolment 2024/25**: the Faculty's Class of 2024/25 profile book prints only a sex split (BCL 45 female + 67 male; MJur 25 female + 20 male) and no class total. The row is retained with `enrolled` blank rather than summing subgroups.
- No official annual graduate count for the BCL or MJur was located.

## London School of Economics — LL.M. (Master of Laws)

- LSE's published programme-level admission tables cover **2020/21 and 2021/22 entry only** at the public URLs cited in `batch_b.csv`. Spreadsheets for 2019/20 and for 2022/23 onwards were not found at the published Information Records Management paths or in the Internet Archive captures of those paths (checked 2 Nov 2026). LSE's Planning Division also publishes an interactive "Applications, Offers and Entrants" dashboard on Tableau Public, but no downloadable programme-level table was retrievable from it.
- **Graduates**: LSE does not publish degrees awarded by programme; no graduate count is available for the LL.M.

## What is usable for production-versus-intake analysis

- Oxford: enrolment by cohort for BCL and MJur, 2019-2025 (2024 blank, sex split only).
- Harvard: enrolment for 2019 and 2021-2025; LL.M. degrees conferred for 2019-2024.
- LSE: applications, offers and registrations for 2020 and 2021 entry.
- Cambridge: nothing at programme level.

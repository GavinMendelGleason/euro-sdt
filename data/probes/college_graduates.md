# College of Europe — annual graduate counts

Probe: `college_graduates`. Question: how many students does the College of
Europe award a master's degree to each year, 2019–2025?

## Bottom line

**No official source publishes an annual count of College of Europe graduates
for any year in 2019–2025.** Every institution that could plausibly hold the
number was checked; each either publishes enrolment instead, publishes a
completion *rate* instead, or publishes a cumulative alumni stock.

What is published, exactly:

| Quantity | Value | Year | Source |
|---|---|---|---|
| Students per promotion (all campuses) | 468, 471, 479, 472, 472, 460, 494 | 2018-19 … 2024-25 | College "Promotions and Patrons" table |
| Enrolment, 2024-25 | **496** ("a new enrolment record") | 2024-25 | Rector's 2020-2025 mandate report |
| Enrolment, 2024 (campus breakdown) | 340 Bruges + 120 Natolin + 32 Tirana = 492 | 2024 | Press factsheet |
| Natolin EIS enrolment | 133 (2019-20), 137 (2018-19) | — | Natolin Activity Report 2009-2019 |
| Qualification obtained within one year | "More than 90%" | 2017 assessment | VLUHR/NVAO assessment report |
| Qualification at first exam session | "Circa 75%" | 2017 assessment | VLUHR/NVAO assessment report |
| Natolin graduation rate | 93% (2009-2019), 94.7% (2019-20), 97.8% (2020-21), ">93% since 2009" | — | Natolin activity reports |
| Natolin completion rate | 100% in 2019-20 and 2020-21 ("same number of students started and finished") | — | Natolin Activity Report 2026 |
| Alumni, cumulative | 17,000+ (2024); 14,500 (2020) | — | Factsheet; 2020 brochure |
| Natolin alumni, cumulative | "Over 3,300 … since 1992" | 2026 report | Natolin Activity Report 2026 |
| IRD programme alumni, cumulative | "more than 1600" over 20 years | 2026 | College careers page |

## Why the number is absent, source class by source class

**College of Europe institutional reports.** The Rector's 2020-2025 mandate
report (the College's own five-year review) reports applications, enrolment
and scholarships, and prints a "Student numbers 2018-2025" chart, but no
degree count. The Natolin 2009-2019 activity report and the Natolin 2026
activity report both discuss graduation only as a rate. The brochures
(2015-16, 2018, 2019, 2020 and 2026 editions) and the press factsheet give
student and alumni totals only.

**VLUHR / NVAO (Flemish accreditation).** Four reports were read: the 2017
educational assessment of the five master's programmes (the source of the
90%/75% figures), the 2018 NVAO report for the LLM, the 2021 MATA assessment
report, and the 2026 VLUHR programme review. None contains a graduate count or
a cohort table; the 2010 LLM report is a scanned image with no text layer.
NVAO classifies the College as a "Non-statutory registered institute".

**Flemish higher-education register and statistics.** The College does not
appear in the Flemish Community's official list of higher-education
institutions and programmes (*Wat kan je waar studeren 2023*; no "College of
Europe" or "Europacollege" entry). The Flemish diploma statistics
(Dataloep / Statistiek Vlaanderen, sourced from the Databank Hoger Onderwijs)
therefore do not cover it, and its graduates are not in those counts. This was
checked because the College's degrees are NVAO-accredited and it is sometimes
described as Flemish-recognised; accreditation does not put it in the Flemish
diploma databank.

**Annual accounts.** The College is a Belgian private institution of public
utility (*établissement d'utilité publique* / *stichting van openbaar nut*). Its
annual accounts are filed with the National Bank (CBSO/Balanscentrale), which
publishes balance sheet, profit and loss and social balance sheet. There is no
student or graduate line, by construction.

**Alumni association.** The 2024-2025 activity report gives engagement
figures ("nearly 3,000 alumni actively participate", "more than 9,000 alumni
connected through the Hivebrite platform"), not a per-promotion graduate
count. The pages of its public news archive that were read (newest first, down
to 2020) carry no graduate counts either.

**EU education contracts.** The College delivers the EU Diplomatic Academy for
the EEAS. The EEAS reports participants per cohort, not College master's
graduates (see the `euda_participants` row: 22 in 2023-24). The Council
decision establishing the EUDA (21 May 2024) gives a budget (€1.7m for
2024-25) and no participant or graduate numbers.

**Other checks that failed.** The Belgian Chamber budget justification
54/2110 (which mentions the College) was not retrievable as a PDF from
`dekamer.be` (the request returned a 246-byte HTML stub). The Polish NIK control report
(kno~p_20_023) concerns MFA scholarship programmes, not College graduates. No
archived College annual report PDF was found in the Wayback CDX index (the old
`download2.asp?file=Annual Report 2002-2003.pdf` link is archived only as a
404). Several College pages returned HTTP 403 (Cloudflare) to direct fetches;
those that mattered were read through the Wayback Machine instead.

## Exact quotes

- Rector's mandate report: "The academic year 2024-25 … brought, with 496
  students, a new enrolment record in the institution's history." The same
  report says combined enrolment was "in the range of 460 to 476 in the period
  2020-21 to 2024-25" — 496 is inconsistent with that range, and the two
  figures are reported separately rather than reconciled.
- VLUHR/NVAO 2017: "More than 90% of all students obtain the qualification
  within one year. Circa 75% of all students attain the qualification during
  the first exam session."
- Natolin 2009-2019: "Over the last ten years, 93 per cent of those who
  completed the year received their diplomas."
- Natolin 2026: "The academic year 2019/2020 saw a 100% completion rate,
  meaning that the same number of students started and finished their academic
  year. In the academic year 2020/2021, the figure was the same. The graduation
  rate remained high at 94.7% in 2019/2020, and 97.8% in 2020/2021."
- Natolin 2026: "an average graduation rate exceeding 93% since 2009."

## Arithmetic bounds — assumptions, not observations

If a production figure is needed before an official count is obtained, the
only defensible construction is enrolment × completion, labelled as an
assumption:

- 2024-25, all campuses: 496 × 0.90 = 446 to 496 × 1.00 = 496.
- 2019-20 to 2023-24 cohorts (468, 471, 479, 472, 472, 460): 0.90 × cohort
  gives 414–431 per year.
- Natolin 2019-20: 133 enrolled × 100% completion × 94.7% graduation ≈ 126.

These are ranges derived from published inputs, not counts. They must not be
entered in a `graduates` field as if observed, and the cumulative alumni rows
(17,000+; 3,300 Natolin; 1,600 IRD) must never be summed with annual flows.

## What would close the gap

The number exists inside the College: the Natolin report cites "internal data"
for its graduation-rate figures and the promotions table implies a registrar's
count per promotion. It is not in any published document found. The realistic
routes are (a) a direct request to the College registrar / Communications
Office for degrees awarded per promotion, or (b) a written question to the
Flemish Parliament or the College's board, where the Flemish Community is
represented.

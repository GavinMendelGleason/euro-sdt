# Historical gating-institution series: sources

## College of Europe
- **Source:** College of Europe, *Promotions and Patrons*, table column "Students".
- **URL:** https://www.coleurope.eu/about-college/history/promotions-and-patrons
- **Local snapshot:** `sources/official/probes/college-of-europe-promotions-and-patrons-2026.txt`
- **Years:** 1950–2024. **Metric:** matriculated students per promotion, not graduates.

## Harvard LL.M.
- **1983–1989:** NCES/IPEDS Completions, Harvard UNITID 166027, CIP 22.0101, award level 9. API: `https://educationdata.urban.org/api/v1/college-university/ipeds/completions-cip-6/1985/?unitid=166027&cipcode_6digit=220101&race=99&sex=99`
- **1990–1995:** Harvard Fact Book 1996–97, "Degrees Conferred: FY1991–1996", Internet Archive: `https://web.archive.org/web/20020320082926/http://vpf-web.harvard.edu/factbook/96-97/page11.htm`
- **1996–2001:** Harvard Fact Book 2002–03, "Degrees Conferred", p. 14: `https://oira.harvard.edu/files/2023/02/harvard_fact_book_2002-2003.pdf`
- **2002–2006:** Harvard Fact Book 2007–08, p. 15: `https://oira.harvard.edu/files/2023/02/harvard_fact_book_2007-2008.pdf`
- **2007–2011:** Harvard Fact Book 2011–12, p. 11: `https://oira.harvard.edu/files/2023/02/harvard_fact_book_2011-12_final.pdf`
- **2009–2016:** Harvard Fact Book 2016–17, Table 3.2: `https://oira.harvard.edu/files/2025/11/Factbook_2016_2017.pdf`
- **2016–2024:** OIRA, "Degrees Conferred by School and Degree: AY2016–25": `https://oira.harvard.edu/factbook/fact-book-degrees`
- **Metric:** LL.M. degrees conferred. The 2020 value of 59 is a COVID-year institutional figure, not missing data.

## École Polytechnique
- **Source:** SCEI, *Statistiques des concours*, École Polytechnique entrant rows.
- **Index:** `https://www.scei-concours.fr/statistiques.html`
- **Years:** 2002–2025. **Metric:** entrants/admitted, French CPGE cycle; 2002–2019 extracted annually from SCEI. Étranger and voie-universitaire rows are excluded.
- **Note:** the flat 379–397 band is genuine; the booklet series including the university channel is 425–431 after 2020.

## Oxford BCL/MJur
- **Source:** Oxford Faculty of Law, Board of Examiners' reports, statistics appendices.
- **Years:** 2002–2019. **Metric:** candidates examined, not enrolment or graduates.
- **Example URLs:** `https://www.law.ox.ac.uk/sites/default/files/migrated/bclexam2002.pdf`; `.../bclexam2010.pdf`; `.../bcl_mjur_examiners_report_2_2015.pdf`; `.../examiners_report_2019._final_draft.pdf`
- **Gaps:** 2004 entirely; BCL 2005. The post-2019 series is enrolment, so it is not concatenated.

## Cologne law
- **Source:** University of Cologne, *Zahlen | Daten | Fakten* (ZDF), first-examination graduates.
- **Years:** 2011–2024. **Metric:** successful first-examination graduates (heads).
- **ZDF 2015:** `https://strategy.uni-koeln.de/e143393/e143429/e105942/akkordeon_oeffner105943/text105953/ZDF_2016_12_22_komprimiert_ger.pdf`
- **ZDF 2016:** `.../text105952/ZahlenIDatenIFakten2016_WEB-Version_ger.pdf`
- **ZDF 2019:** `.../text105949/ZDF_AW_web_compressed_FINAL_ger.pdf`
- **ZDF 2024:** `https://strategy.uni-koeln.de/e143393/e143429/e108817/ZDF_2024_web_interaktiv_JUNI2026_ger.pdf`

## LSE LLM
- **Source:** LSE Planning Division, *Student Statistics*, Table F "Taught Masters Students by Programme".
- **URL:** `https://info.lse.ac.uk/staff/divisions/Planning-Division/Assets/Documents/Student-Statistics-2021.pdf`
- **Years:** 2014/15–2020/21. **Metric:** enrolled LLM headcount (1st year plus subsequent years).
- The older two-point admissions workbook measured registrations, not enrolment; it has been removed from this series.

## ENA/INSP
- **Current output source:** ENA/INSP activity reports 2019–2025.
- **Earlier official series found:** places offered at the entrance concours, 2006–2020, from ENA activity reports (e.g. `https://www.documentation-administrative.gouv.fr/adm-01859770v1/file/ENA_RA_2020.pdf`).
- **Limitation:** places offered is not enrolment or graduation; no public annual output series before 2019 was located.


## Population denominator

- **Source:** World Bank, `SP.POP.TOTL`, annual population by country, 1960–2025.
- **Construction:** sum of the member states at each date; membership timeline is recorded in `data/institutions/eu_population.csv`.
- **Coverage:** 1960–2025 only. Pre-1960 output is not normalised.


## Extension status

### Cologne 2010 onward
- ZDF 2011/12, p. 60: `https://web.archive.org/web/20210413211301/https://strategy.uni-koeln.de/e143393/e143429/e145027/ZDF_2011_12_ger.pdf`
- ZDF 2012/13, p. 60: `https://web.archive.org/web/20210413194035/https://strategy.uni-koeln.de/e143393/e143429/e145026/ZDF_2012_13_ger.pdf`
- ZDF 2014/15, p. 58: `https://web.archive.org/web/20210414021704/https://strategy.uni-koeln.de/e143393/e143429/e144953/ZDF_2014_2015_V3_ger.pdf`
- 2007 excluded: old-law backlog, not comparable. 2008 and 2009 omitted: incomplete IT.NRW report; the 2008 late report is folded into 2009. Comparable series starts 2010.

### LSE before 2014/15
- No numeric LLM series. LSE Digest degree-award lists exist for 2003-04 to 2012-13 but have names only, not counts; a derived count would be a graduates series, not enrolled headcount.

### ENA before 2019
- No compiled output series. Only places offered (2006-2020) is tabulated. Promotion sizes and graduate counts exist only in Journal officiel name lists; Légifrance blocks automated access, and mirrored texts require name-by-name counting.


## Display-year convention

In the per-capita chart, College of Europe, Harvard, and LSE are displayed at academic-year end: their 2024--25 observations are plotted in 2025. This is a display convention; `institution_cohort.year` retains the source year label. Oxford (examination year), Cologne (examination year), Polytechnique (entrants), and ENA (promotion entry) remain as recorded.

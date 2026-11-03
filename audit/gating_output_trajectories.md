# Gating-institution output trajectories

The relevant temporal object is the institution's output of qualified people, not its applicants. The series below are not a common measure: each panel uses the institution's own reported series. A single indexed overlay is at `assets/papers/methodology/gating-trajectories-overlay.png`; each line is set to 100 at its first observation and plotted on a log scale.

| Institution | Series | Years | Metric | Trajectory |
|---|---|---|---|---|
| College of Europe | matriculation | 1950–2024 | students | 35 (1950) → 131 (1980) → 145 (1990) → 494 (2024) |
| Harvard LL.M. | degrees conferred | 1983–2024 | LL.M. degrees | 95 (1983) → 190 (2018) → 59 (2020) → 175 (2024) |
| École Polytechnique | entrants/admitted | 2002–2025 | entrants | 383 (2002) → 379–397 (2002–19) → 431 (2020–25) |
| Oxford BCL/MJur | candidates examined | 2002–2019 | examined | BCL 67 → 111; MJur 61 → 38 |
| Cologne law | first-examination graduates | 2010–2024 | graduates | 444 (2010) → 358 (2011) → 320 (2014) → 484 (2019) → 420 (2024) |
| LSE LLM | enrolled headcount | 2014–2020 | enrolled | 277 (2014/15) → 273 (2020/21) |
| ENA/INSP | initial-training enrolment | 2019–2025 | enrolled | 80 (2019) → 89 (2024) → 61 (2025) |

## What the longer series show

- **College of Europe:** sustained expansion, mostly before 2000; the 1990 value is not the start of the series.
- **Harvard LL.M.:** stable band of roughly 130–180 degrees, not a growth trend; 2020 is a COVID-year exception.
- **École Polytechnique:** a flat 379–397 band from 2002 to 2019, then a higher 425–431 plateau.
- **Oxford BCL/MJur:** BCL expanded while MJur contracted; the series is volatile and ends in 2019 because the later metric is enrolment, not examinations.
- **Cologne law:** no monotonic expansion; a mid-2010s trough and partial recovery. The 2007 old-law backlog and 2008–09 incomplete reports are excluded.
- **LSE LLM:** a short but genuine enrolled series from 2014/15; it does not support a trend claim.
- **ENA/INSP:** still only a recent window; no public annual output series before 2019 was located.

## Why some series still start late

The start dates are acquisition and publication boundaries, not the institutions' founding dates:

- **ENA/INSP:** annual reports from 2019 onward contain enrolment counts. Earlier annual reports are not digitized; the only earlier official series found is **places offered** (2006–2020), not output.
- **École Polytechnique:** SCEI concours statistics begin in 2002. The JORF admission arrêtés go back to 1990 but are name lists behind a blocked legal database.
- **Oxford:** Faculty of Law Board of Examiners' reports provide examined-candidate counts from 2002; pre-2002 programme-level numbers are not public.
- **Cologne:** the university's *Zahlen | Daten | Fakten* series gives the same 2011–2024 definitions; earlier graduate counts are not published at university level.
- **LSE:** Student Statistics Table F retains only 2014/15 onward; earlier LLM-specific counts are not public.
- **Harvard:** the federal IPEDS series starts in 1983; earlier years require restricted HEGIS microdata.

## Sources

Detailed URLs and extraction notes: `audit/historical_series_sources.md`. Machine-readable rows: `data/institutions/historical_series.csv`.


## Per-capita version

`assets/papers/methodology/gating-trajectories-per-capita.png` divides each output series by the **EU/EC population of the member states at that date** and expresses the result per 100,000 population. It includes a dashed **mean of available series** line: an unweighted mean across institutions with a value in that year. A mean is computed every year with at least one available series; the number of contributing series is annotated at the endpoints. The mean is descriptive and its composition changes as series enter and leave. In 2024 five series contribute; in 2025 only Polytechnique and ENA/INSP remain, so the endpoint reflects a two-series mean, not a general decline.

- Denominator: World Bank `SP.POP.TOTL`, summed over the member states at each date.
- Membership: EU-6 in 1960; EU-9 from 1973; EU-10 from 1981; EU-12 from 1986; EU-15 from 1995; EU-25 from 2004; EU-27 from 2007; EU-28 from 2013; EU-27 after the UK's 2020 withdrawal.
- Vertical lines mark those accession/withdrawal dates.
- Pre-1960 output is not plotted because the population series starts in 1960.
- The numerator units still differ (degrees, entrants, examined candidates, enrolled students), so the per-capita lines are comparable in denominator, not in numerator definition.


## Extension attempts

- **Cologne:** the comparable series starts in 2010. The 2007 old-law backlog is excluded as non-comparable; 2008 and 2009 are omitted because the university marks 2008 as an incomplete IT.NRW report and folds it into 2009. Pre-2007 university-specific counts were not located.
- **LSE:** no official numeric LLM series before 2014/15. The LSE Digest has named degree-award lists from 2003–04 to 2012–13, but no printed totals; counting them would create a separate graduates series, not an enrolled-headcount extension.
- **ENA/INSP:** no compiled annual output series before 2019, but pre-2019 observations exist: places offered 2006–2021; a 2014 cohort of 80; a 2016 cohort of 89; 104 admitted for 1993; 105 graduates in 1996; and a 2018 stock of 177 French students across two overlapping promotions. These are different metrics and are not spliced into one line. Pre-2006 cohort counts require counting Journal officiel name lists.

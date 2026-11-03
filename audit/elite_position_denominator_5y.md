# Elite-position denominator: five-year panel

## Definition

\[
D_t = A_t + B_t + C_t
\]

- **A:** European Commission establishment-plan posts, all grades, all budgets.
- **B:** bar-admitted lawyers in Germany, France, and Italy.
- **C:** board seats of publicly traded companies in Germany, France, and Italy.

Years: 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025.

File: `data/denominator/elite_position_denominator_5y.csv`.

## Panel

| Year | A posts | B lawyers | C seats | Total | D |
|---:|---:|---:|---:|---:|---:|
| 1990 | 16,838 | 131,514 | 9,137 | 157,489 |
| 1995 | 19,485 | 188,959 | 13,456 | 221,900 |
| 2000 | 21,798 | 260,112 | 16,716 | 298,626 |
| 2005 | 23,911 | 337,423 | 12,877 | 374,211 |
| 2010 | 25,828 | 416,971 | 12,683 | 455,482 |
| 2015 | 24,299 | 460,186 | 10,174 | 494,659 |
| 2020 | 23,606 | 474,974 | 8,633 | 507,213 |
| 2025 | 23,356 | 474,102 | 7,771 | 505,229 |

## A: Commission

All-budget establishment-plan posts, all grades. The official series is sparse for the all-budget definition, so the 1990–2020 values are linear interpolations between official anchors:

- 1989: 16,309
- 1999: 21,603
- 2002: ~22,187
- 2009: 26,209
- 2012: 25,065
- 2016: 24,044
- 2017: 23,756
- 2025: 23,356
- 2026: 23,357

The 2025 value is observed. Do not mix this with the operating-budget series (18,797 in 2026), which is a narrower establishment plan.

## B: lawyers

Panel uses the bar-roll definition:

| Year | Germany | France | Italy | B |
|---:|---:|---:|---:|---:|
| 1990 | 56,638 | 18,076 | 56,800 | 131,514 |
| 1995 | 74,291 | 29,368 | 85,300 | 188,959 |
| 2000 | 104,067 | 36,445 | 119,600 | 260,112 |
| 2005 | 132,569 | 44,054 | 160,800 | 337,423 |
| 2010 | 153,251 | 51,758 | 211,962 | 416,971 |
| 2015 | 163,513 | 62,073 | 234,600 | 460,186 |
| 2020 | 165,901 | 70,073 | 239,000 | 474,974 |
| 2025 | 166,504 | 77,598 | 230,000 | 474,102 |

- Germany: BRAK, 1 January. 1990 is pre-reunification West Germany; 1992 is missing.
- France: DACS, 1 January. 1990 is 1989 avocats-only, **before** the 1992 merger with conseils juridiques; it is not comparable with later values.
- Italy: bar-roll/CEPEJ basis, with 1990, 1995, 2000, 2005, 2015, 2020, and 2025 estimated; 2010 observed. Cassa Forense is continuous but is a pension-membership series and has a +26.4% break in 2014; it was not used for the bar-roll series.

## C: listed boards

| Year | Germany | France | Italy | C |
|---:|---:|---:|---:|---:|
| 1990 | 3,304 | 3,633 | 2,200 | 9,137 |
| 1995 | 5,560 | 5,396 | 2,500 | 13,456 |
| 2000 | 6,250 | 7,466 | 3,000 | 16,716 |
| 2005 | 5,184 | 4,943 | 2,750 | 12,877 |
| 2010 | 5,341 | 4,442 | 2,900 | 12,683 |
| 2015 | 4,163 | 3,675 | 2,336 | 10,174 |
| 2020 | 3,197 | 3,280 | 2,156 | 8,633 |
| 2025 | 2,954 | 2,890 | 1,927 | 7,771 |

C = listed domestic companies × average board seats per company, with observed governance studies where available and documented interpolation/extrapolation elsewhere. Seats, not unique persons. Germany counts Aufsichtsrat + Vorstand; France counts conseil d'administration/surveillance; Italy counts consiglio di amministrazione and excludes collegio sindacale. Employee representatives are included.

## Caution

- This is a five-year stock panel, not an annual time series.
- A is posts; B is persons; C is seats. They are not identical units.
- The 1990 French lawyer value is on the pre-merger basis; the 1990–2005 C values are substantially estimated.
- The panel is suitable as a scale denominator, not for precise year-over-year growth.

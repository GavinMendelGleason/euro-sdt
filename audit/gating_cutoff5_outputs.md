# Cutoff ≥5 output data

Institution-wide degree or graduate series collected for the 12 cutoff-≥5 institutions that previously had no output.

| Institution | Years obtained | Metric | Coverage |
|---|---|---|---|
| Cambridge | 2000–2015, gaps 2010–11/2011–12 | degrees conferred | partial |
| Cambridge | 2014–2021 | HESA HE qualifiers | partial, different metric |
| Georgetown | 2000–2024, 2020 omitted | degrees awarded | near-complete |
| UCLouvain | 2000 and 2020 | degrees awarded | endpoint observations only |
| ULB | 2000 and 2020 | degrees awarded | endpoint observations only |
| Stockholm | 2000–2024 | degrees/examinations | near-complete |
| Tartu | 2007–2025 | graduates | partial |
| Vilnius | 2019–2025 | graduates | recent only |
| Ljubljana | 2010–2014, 2018–2025 | graduates | partial |
| Malta | 2022–2023 graduation cycles | degrees | two points |
| Paris II | 2015–2021 | degrees awarded | partial |
| Athens | 2020–2023 | graduates | recent only |
| Charles | 2024 | graduates | one point |

File: `data/analysis/gating_cutoff5_outputs.csv`.

## Comparability

- Degrees, qualifiers, graduates and examinations are **not the same measure**.
- Some series are academic-year, some calendar-year, some graduation-cycle.
- Multiple awards per person may be counted separately in Cambridge, Stockholm and the Belgian series.
- Cambridge’s degree series and HESA qualifier series must not be concatenated.
- Georgetown 2020 is omitted: the IPEDS extract repeats 2019 exactly.
- UCLouvain/ULB have only endpoint observations; they cannot support a chained annual series.
- The 2004 Bologna reform and programme mergers break the Belgian series.
- Malta’s counts are graduation-cycle, not calendar-year.

## Consequence

Output data now exists in some form for every cutoff-≥5 institution, but only Stockholm and Tartu are close to a usable annual panel. There is not yet a harmonised series that can be divided by the A/B/C position denominator to produce a credible overproduction test.

The next step is to choose one metric — total degrees awarded — and either acquire the missing years for Cambridge, UCLouvain, ULB, Vilnius, Ljubljana, Malta, Paris II, Athens and Charles, or restrict the comparison to a common window.

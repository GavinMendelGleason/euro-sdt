# Degrees awarded: available series

## What is genuinely a degree count

| Institution | Programme | Years | Source | Notes |
|---|---|---|---|---|
| Harvard | LL.M. | 1983–2024 | Harvard Fact Books / OIRA / IPEDS | LL.M. degrees conferred |
| Bocconi | Law (Giuridico / LMG/01) | 2003–2025 | MUR/USTAT `Laureati` | 2004 reform break; law group |
| Bocconi | Economics/management (Economico) | 2010–2025 | MUR/USTAT `Laureati` | discipline-group aggregate, not single programme |
| LUISS | Law (Giuridico / LMG/01) | 2001–2025 | MUR/USTAT `Laureati` | 2004 reform break; law group |
| École Polytechnique | Engineering degree | 1995, 2024 | Journal officiel degree lists | observed points only; no annual series |

## What is not a degree count

- **Oxford / LSE:** HESA Table 16 gives **HE qualifiers at all levels**, not degrees only; 2014/15–2021/22 available. It is institution-wide, not BCL/MJur or LLM-specific.
- **Cologne:** the existing series is **first-examination passes**, not university degrees. Cologne's actual `Magister iuris` / `Diplom-Jurist` awards are application-based and not published annually.
- **ENA/INSP:** exit is an *arrêté d'affectation* and attestation, not a degree; no degree series.
- **College of Europe:** no annual degree count is published; only matriculation and completion rates.

## File

`data/institutions/degrees_awarded.csv` contains observed degree or qualifier rows with metric and source. Do not sum across metrics. HESA qualifiers are not equivalent to degrees; Bocconi/LUISS law degrees are not equivalent to first-examination passes.

## Practical consequence

A degree-based replacement is only possible for Harvard and for a new Bocconi/LUISS law series. Oxford, LSE, Cologne, ENA and the College cannot be converted from their current measures without either estimating or changing the construct.


## Bocconi economic elites in the corpus

`audit/education_aggregate_non_mep.md` records 5 observed people educated at Bocconi: 2 commissioners and 3 corporate elites. The economics/management series is the relevant degree context for the economic-elite side; the law series is separate.

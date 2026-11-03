# Institution data gathering

## Gathered

### Programme cohorts

`institution_cohort` now holds **235 rows** across eight institutions. The authoritative catalogue is `data/institutions/time_series_index.csv`; this section is a snapshot and may lag.

| Institution | Rows | Years |
|---|---:|---|
| College of Europe | 2 | 2019, 2024 |
| ENA / INSP | 9 | 2019–2025 |
| École Polytechnique | 12 | 2020–2025 |
| Harvard LL.M. | 7 | 2019–2025 |
| LSE LLM | 2 | 2020–2021 |
| University of Oxford BCL/MJur | 14 | 2019–2025 |
| University of Cologne law | 6 | 2019–2024 |
| Vilnius University law | 1 | 2025 |

Field completeness:

| Field | Rows |
|---|---:|
| Applicants | 24 |
| Admitted | 18 |
| Enrolled | 46 |
| Graduates | 12 |

Cambridge and UCLouvain have no programme-level rows; the missing files document why.

### CJEU openings

`position_census` now holds **51 annual opening rows** for 2019–2025:

| Track | Annual rows | Openings |
|---|---:|---:|
| Court of Justice judges | 18 | 18 |
| Advocates General | 13 | 10 |
| General Court judges | 20 | 37 |

Openings exclude renewals of incumbents. Zero-opening years are retained.

## Not yet computable

No `placement_rate` or `overproduction_ratio` is yet valid:

- Cohorts and openings are not matched by institution-specific intake year.
- College of Europe has enrolment but no graduate count.
- Harvard has graduates but not applicants/admissions.
- Oxford has enrolment but no graduate count.
- The CJEU openings are not yet linked to the educational institutions of the appointees.
- Commission, DG/DDG and corporate-board annual openings remain missing.

## Next

1. Build `role_intake` from dated appointments.
2. Link each intake to the person's education institution(s).
3. Use graduate cohorts, not enrolment, as production.
4. Compute only where cohort, intake and openings are jointly observed.

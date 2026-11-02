# Institution layer

## Built

- `institution_profile`: 10 top education institutions, provisional profiles.
- `position_census`: 6 current stock counts:
  - Court of Justice: 27 Judges, 11 Advocates General, 1 Registrar.
  - General Court: 53 Judges on the rendered roster; official prose states 54.
  - Commission: 27 Commissioners; 85 DGs/DDGs from the internal frame.
- `institution_metric`: 40 observed institution–track rows for the top 10 institutions.
- `graph/institution_metrics.csv`: graph-ready observed metrics.

## Important status

`institution_metric.production`, `openings`, `placement_rate`, and `overproduction_ratio` are **null**. The current data contains observed alumni and current role holders, not:

- annual admissions or graduate cohorts;
- annual position openings;
- role-entry events with dates.

Therefore no production-versus-intake ratio is computed yet.

## Position census caveat

The position table stores **stock**, not annual openings. A 27-judge court does not have 27 openings per year. `openings` must be collected from annual appointment/retirement data.

## Next acquisition

For each selected institution:

1. annual applicants, admitted, enrolled, graduates;
2. programme and cohort year;
3. role-entry event and year;
4. annual position openings by track.

Without those, the graph can show observed alumni concentration but cannot support elite overproduction claims.

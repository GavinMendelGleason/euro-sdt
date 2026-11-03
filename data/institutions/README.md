# Institution time series

## Primary store

`euro_sdt_v2.db`, table `institution_cohort`.

Each row is an institution–programme–year observation, with optional fields:

- `applicants`
- `admitted`
- `enrolled`
- `graduates`

and provenance in `source_url`, `source_file`, and `notes`.

## Index

`data/institutions/time_series_index.csv` is the catalogue of time series.

Columns: `series_id`, `institution_id`, `programme`, `metric`, `first_year`, `last_year`, `n_obs`, `has_gaps`, `storage`, `chart`, `source_urls`, `notes`.

The index is generated from the database plus the two CSV-only series:

```bash
.venv/bin/python scripts/build_time_series_index.py
```

## Files

| File | Role |
|---|---|
| `historical_series.csv` | Staging extract of historical rows inserted into `institution_cohort`; the database is authoritative. |
| `cohort_fragments/` | Raw acquisition fragments and missing-data notes; not the analysis layer. |
| `ena_places_offered.csv` | ENA places offered, 2006–2021. Not an output measure. |
| `eu_population.csv` | EU/EC member-state population by year, 1960–2025. |
| `eu_member_population_wb.json` | World Bank country population cache used to construct `eu_population.csv`. |
| `time_series_index.csv` | Catalogue of all series and their coverage. |

## Coverage caveats

- A series is one `institution_id` + `programme` + metric. Programme-level fragments can therefore appear as one-observation series.
- `has_gaps=yes` means the first-to-last range contains missing years.
- The main analytical series are the programme-level rows used by `scripts/plot_gating_trajectories_individual.py`; the index includes the ENA historical fragments as well.
- ENA historical observations mix places offered, admitted cohorts, enrolment, and graduates. They are deliberately not merged into one line.

## Charts

| Chart | Script |
|---|---|
| `assets/papers/methodology/gating-trajectories-combined.png` | `scripts/plot_gating_combined.py` |
| `assets/papers/methodology/gating-trajectories-per-capita.png` | `scripts/plot_gating_per_capita.py` |
| `assets/papers/methodology/gating-trajectories-chained-index.png` | `scripts/plot_gating_chained_index.py` |
| `assets/papers/methodology/ena-insp-history.png` | `scripts/plot_ena_history.py` |
| `assets/papers/methodology/gating-trajectories/*.png` | `scripts/plot_gating_trajectories_individual.py` |

Reports: `audit/gating_output_trajectories.md` and `audit/historical_series_sources.md`.

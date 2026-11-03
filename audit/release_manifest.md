# Release manifest

Frozen analysis release for the paper body.

| Item | Value |
|---|---|
| Git commit | `214d7e2a505dae4a8004f85eba3e27ebb2639393` |
| Database | `euro_sdt_v2.db` |
| Database SHA-256 | `2f1da1b7589ddcd001b6ba529e4b6bccb3b8d18aa6b13ef2201c860c4085713f` |
| Claims | 6,716 |
| Assertions | 6,716 |
| Source documents | 994 |
| Sentences | 51,302 |
| Evidence rows | 7,485 |
| Entities | 4,842 |

## Published analysis artifacts

- `assets/papers/methodology/paper.tex`
- `assets/papers/methodology/paper.pdf`
- `data/institutions/time_series_index.csv`
- `data/institutions/historical_series.csv`
- `data/institutions/ena_places_offered.csv`
- `data/institutions/eu_population.csv`
- `data/denominator/elite_position_denominator_5y.csv`
- `data/denominator/elite_school_denominator_index_5y.csv`
- `graph/nodes.csv`, `graph/edges.csv`, `graph/graphml`

## Reproduction boundary

Reproducing the published tables from the frozen accepted records requires the database and scripts, not new model calls. Re-running extraction or adjudication may call an external API and may produce different decisions. Model identifiers and cache state are in `run` and the adjudication caches.

## Checks

```bash
.venv/bin/python scripts/check_v2.py
.venv/bin/python scripts/build_time_series_index.py
.venv/bin/python scripts/build_elite_position_denominator.py
.venv/bin/python scripts/plot_elite_school_denominator_index.py
.venv/bin/python scripts/plot_elite_school_A_C.py
cd assets/papers/methodology && latexmk -pdf paper.tex
```

# Verified Elite Graph

Generated from `euro_sdt_v2.db`. Only `assertion.status = 'verified'` appears here.

## Summary

| Metric | All verified | Grade A only | Network edges only |
|---|---:|---:|---:|
| Nodes | 2900 | 2225 | 2191 |
| Edges | 3723 | 2628 | 2692 |
| Unique person–entity pairs | 3486 | 2526 | 2549 |
| Largest component | 2664 | 1903 | 1956 |
| Degree-1 nodes | 2205 | 1672 | 1649 |

## Edges by class

| Class | Edges |
|---|---:|
| education | 541 |
| institutional | 98 |
| network | 2692 |
| occupational | 389 |
| other | 3 |

## Edges by evidence grade

| Grade | Edges |
|---|---:|
| A | 2628 |
| B | 458 |
| C | 637 |

## Top hubs (all verified edges)

| Entity | Kind | Degree |
|---|---|---:|
| European Commission | organisation | 77 |
| European Parliament | organisation | 51 |
| Kaja Kallas | person | 42 |
| Thierry Breton | person | 39 |
| Neelie Kroes | person | 36 |
| Pascal Lamy | person | 36 |
| Ria Oomen-Ruijten | person | 34 |
| Federica Mogherini | person | 33 |
| Pierre Moscovici | person | 32 |
| Mario Monti | person | 30 |
| António Vitorino | person | 29 |
| Günther Oettinger | person | 29 |
| José Manuel Barroso | person | 29 |
| European People's Party | organisation | 28 |
| Anita Gradin | person | 27 |

## Top co-affiliations

| Person A | Person B | Shared organisations |
|---|---|---:|
| Jutta Urpilainen | Wopke Hoekstra | 6 |
| Jutta Urpilainen | Magnus Brunner | 5 |
| Magnus Brunner | Wopke Hoekstra | 5 |
| Christophe Hansen | Joseph Daul | 4 |
| Godelieve Quisthoudt-Rowohl | Joseph Daul | 4 |
| Godelieve Quisthoudt-Rowohl | Ursula von der Leyen | 4 |
| Andrus Ansip | Kaja Kallas | 4 |
| Erkki Liikanen | Olli Rehn | 4 |
| António Vitorino | Danuta Hübner | 3 |
| Christos Stylianides | Philippe Busquin | 3 |
| Erkki Liikanen | Pier Carlo Padoan | 3 |
| Joaquín Almunia | Manuel Marin | 3 |
| Connie Hedegaard | Joaquín Almunia | 3 |
| Connie Hedegaard | Mario Monti | 3 |
| Magnus Brunner | Pedro Solbes | 3 |

## Notes

- `network` = membership, board, advisory, chair, founder, fellow, attendee.
- `occupational` = employer and held position.
- `education` = education and degree.
- `institutional` = commission service.
- Every edge carries `quote`, `doc_id`, and `source_url` in `edges.csv`.

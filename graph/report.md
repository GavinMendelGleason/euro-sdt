# Verified Elite Graph

Generated from `euro_sdt_v2.db`. Only `assertion.status = 'verified'` appears here.

## Summary

| Metric | All verified | Grade A only | Network edges only |
|---|---:|---:|---:|
| Nodes | 3101 | 2471 | 2285 |
| Edges | 3884 | 2892 | 2784 |
| Unique person–entity pairs | 3669 | 2777 | 2648 |
| Largest component | 2801 | 2065 | 2049 |
| Degree-1 nodes | 2356 | 1858 | 1737 |

## Edges by class

| Class | Edges |
|---|---:|
| award | 3 |
| education | 632 |
| institutional | 94 |
| network | 2784 |
| occupational | 369 |
| other | 2 |

## Edges by evidence grade

| Grade | Edges |
|---|---:|
| A | 2892 |
| B | 462 |
| C | 530 |

## Top hubs (all verified edges)

| Entity | Kind | Degree |
|---|---|---:|
| European Commission | organisation | 72 |
| European Parliament | organisation | 54 |
| Kaja Kallas | person | 46 |
| Ursula von der Leyen | person | 43 |
| Henna Virkkunen | person | 35 |
| Pascal Lamy | person | 35 |
| Neelie Kroes | person | 34 |
| Ria Oomen-Ruijten | person | 34 |
| Thierry Breton | person | 33 |
| Wopke Hoekstra | person | 33 |
| Federica Mogherini | person | 32 |
| Pierre Moscovici | person | 32 |
| Mario Monti | person | 30 |
| António Vitorino | person | 29 |
| Günther Oettinger | person | 29 |

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
- `award` = awards received and their awarding body.
- Every edge carries `quote`, `doc_id`, `doc_title`, `doc_path`, and `doc_sha256`.
- `source_url` is empty only for local-only documents (DG CVs, CJEU, declarations); the path and hash identify them.
- 25 verified claims are excluded because an endpoint is quarantined.

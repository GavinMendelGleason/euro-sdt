# Verified Elite Graph

Generated from `euro_sdt_v2.db`. Only `assertion.status = 'verified'` appears here.

## Summary

| Metric | All verified | Grade A only | Network edges only |
|---|---:|---:|---:|
| Nodes | 3226 | 2842 | 2520 |
| Edges | 3850 | 3211 | 2837 |
| Unique person–entity pairs | 3633 | 3080 | 2702 |
| Largest component | 2828 | 2395 | 2024 |
| Degree-1 nodes | 2670 | 2355 | 2116 |

## Edges by class

| Class | Edges |
|---|---:|
| education | 486 |
| institutional | 94 |
| network | 2837 |
| occupational | 431 |
| other | 2 |

## Edges by evidence grade

| Grade | Edges |
|---|---:|
| A | 3211 |
| B | 297 |
| C | 342 |

## Top hubs (all verified edges)

| Entity | Kind | Degree |
|---|---|---:|
| European Commission | organisation | 71 |
| Kaja Kallas | person | 45 |
| Ursula von der Leyen | person | 43 |
| L'Oréal | organisation | 37 |
| Henna Virkkunen | person | 35 |
| Pascal Lamy | person | 35 |
| Safran | organisation | 35 |
| Neelie Kroes | person | 34 |
| BNP Paribas | organisation | 33 |
| Thierry Breton | person | 33 |
| Wopke Hoekstra | person | 33 |
| Anheuser-Busch InBev | organisation | 32 |
| Federica Mogherini | person | 32 |
| Pierre Moscovici | person | 32 |
| SAP | organisation | 32 |

## Top co-affiliations

| Person A | Person B | Shared organisations |
|---|---|---:|
| Jutta Urpilainen | Wopke Hoekstra | 6 |
| Jutta Urpilainen | Magnus Brunner | 5 |
| Magnus Brunner | Wopke Hoekstra | 5 |
| Erkki Liikanen | Olli Rehn | 4 |
| Andrus Ansip | Kaja Kallas | 4 |
| António Vitorino | Danuta Hübner | 3 |
| Christos Stylianides | Philippe Busquin | 3 |
| Erkki Liikanen | Pier Carlo Padoan | 3 |
| Joaquín Almunia | Manuel Marin | 3 |
| Connie Hedegaard | Joaquín Almunia | 3 |
| Connie Hedegaard | Mario Monti | 3 |
| Magnus Brunner | Pedro Solbes | 3 |
| Magnus Brunner | Thierry Breton | 3 |
| Pedro Solbes | Thierry Breton | 3 |
| Mario Monti | Pascal Lamy | 3 |

## Notes

- `network` = membership, board, advisory, chair, founder, fellow, attendee.
- `occupational` = employer and held position.
- `education` = education and degree.
- `institutional` = commission service.
- `award` = awards received and their awarding body.
- Every edge carries `quote`, `doc_id`, `doc_title`, `doc_path`, and `doc_sha256`.
- `source_url` is empty only for local-only documents (DG CVs, CJEU, declarations); the path and hash identify them.
- 1064 verified claims are excluded because an endpoint is quarantined.

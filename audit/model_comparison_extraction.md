# Extraction Model Comparison

Documents: 4; chunks: 8; same prompt and source text for every model.

| Person | Chunk | Chat rows | Flash rows | Flash reasoning rows | Chat locatable | Flash locatable |
|---|---:|---:|---:|---:|---:|---:|
| Ursula von der Leyen | 0 | 5 | 5 | 0 | 5 | 5 |
| Ursula von der Leyen | 1 | 0 | 0 | 0 | 0 | 0 |
| Federica Mogherini | 0 | 15 | 19 | 0 | 15 | 19 |
| Federica Mogherini | 1 | 6 | 6 | 0 | 6 | 6 |
| Guillaume Faury | 0 | 8 | 8 | 0 | 8 | 8 |
| Guillaume Faury | 1 | 3 | 0 | 2 | 3 | 0 |
| Kaja Kallas | 0 | 31 | 30 | 0 | 31 | 30 |
| Kaja Kallas | 1 | 0 | 0 | 1 | 0 | 0 |

## Relation mix

| Model | Relations |
|---|---|
| chat | {'employed_by': 19, 'party_member': 4, 'affiliated_with': 3, 'member': 19, 'board_member': 14, 'chair': 8, 'fellow': 1} |
| flash | {'employed_by': 17, 'party_member': 4, 'chair': 10, 'member': 21, 'board_member': 14, 'fellow': 1, 'affiliated_with': 1} |
| flash_reasoning | {'employed_by': 2, 'chair': 1} |

## Errors

- ('ursula-von-der-leyen', 'wikipedia-ursula-von-der-leyen', 0, 'flash_reasoning'): RuntimeError: extraction call failed: empty model response
- ('ursula-von-der-leyen', 'wikipedia-ursula-von-der-leyen', 1, 'flash_reasoning'): RuntimeError: extraction call failed: empty model response
- ('federica-mogherini', 'wikipedia-federica-mogherini', 0, 'flash_reasoning'): RuntimeError: extraction call failed: empty model response
- ('federica-mogherini', 'wikipedia-federica-mogherini', 1, 'flash_reasoning'): RuntimeError: extraction call failed: empty model response
- ('guillaume-faury', 'wikipedia-guillaume-faury', 0, 'flash_reasoning'): RuntimeError: extraction call failed: empty model response
- ('kaja-kallas', 'wikipedia-kaja-kallas', 0, 'flash_reasoning'): RuntimeError: extraction call failed: empty model response
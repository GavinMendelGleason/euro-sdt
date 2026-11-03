# Elite-position denominator

`elite_position_denominator.csv` holds the three components and the total.

- **A:** European Commission establishment-plan posts, all grades (2026)
- **B:** lawyers admitted to the bar in Germany, France, and Italy
- **C:** board seats/members of publicly traded companies in Germany, France, and Italy

Run:

```bash
.venv/bin/python scripts/build_elite_position_denominator.py
```

The script sums A + B + C and rewrites the `TOTAL` row.

Method, definitions, sensitivity and caveats: `audit/elite_position_denominator.md`.

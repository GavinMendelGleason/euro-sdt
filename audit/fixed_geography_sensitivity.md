# Fixed-geography population sensitivity

The paper's population denominator changes with EU/EC membership. This sensitivity holds geography fixed at the **2025 EU-27** and sums the current member states' populations back to 1960.

- Data: `data/institutions/eu_population_fixed_2025.csv`
- Current-membership denominator: `data/institutions/eu_population.csv`
- Index: same interpolated chained-median construction as the paper's per-capita index.

| Year | Historical membership | Fixed 2025 EU-27 |
|---|---:|---:|
| 1960 | 100.0 | 100.0 |
| 1980 | 223.2 | 285.5 |
| 2000 | 311.5 | 513.2 |
| 2010 | 256.7 | 530.1 |
| 2020 | 293.8 | 535.8 |
| 2025 | 296.6 | 540.9 |

The difference is the denominator geography, not a change in gating-institution output. The fixed-geography index is substantially higher because the 1960 base excludes the later member states, whereas the historical denominator starts with the EU-6 and expands.

# Balanced cutoff ≥5 output measure

The previous aggregate used a different set of institutions in each year, so its level was not comparable across years.

The replacement uses a **fixed five-institution panel**:

- College of Europe
- Harvard LL.M.
- Cologne law
- Stockholm University
- University of Tartu

All five have observations for 2010–2024. The panel therefore has a constant n and a common window.

\[
\frac{\sum_{i=1}^{5}\text{output}_{i,t}}
{\text{Commission posts}_t + \text{judicial positions}_t}
\times 1000
\]

- 2010: **396.7** per 1,000 positions
- 2016: **350.8**
- 2020: **428.3**
- 2024: **488.4**

File: `data/analysis/gating_cutoff5_balanced_output_per_position.csv`.

This still mixes output measures — matriculation, degrees, first-examination passes and graduates — but the **composition is fixed**, so the level is comparable across years. It is not a harmonised degree total.

The middle panel uses the chained median of institution-level growth, which tolerates entry and exit. The bottom panel compares the College of Europe alone with the composite.

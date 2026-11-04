# Cutoff ≥5: harmonised chained index

![Harmonised cutoff index](assets/papers/methodology/gating-cutoff5-chained-harmonised.png)

## Construction

For each cutoff-≥5 institution:

\[
r_{i,t} = \frac{\text{institution output}_{i,t}}
{\text{Commission posts}_t + 92 \text{ judicial positions}}
\]

The index chains the median annual log growth across institutions observed in consecutive available years:

\[
g_t = \operatorname{median}_{i \in S_t}\log(r_{i,t}/r_{i,t^-})
\]

\[
I_t = 100 \times \exp\left(\sum_{s=2000}^{t} g_s\right)
\]

Observed intervals are annualised and distributed across intervening years. Base 2000 = 100.

## Results

| Year | Index | Growth series |
|---:|---:|---:|
| 2000 | 100.0 | 0 |
| 2005 | 107.2 | 8 |
| 2010 | 119.8 | 9 |
| 2015 | 126.5 | 11 |
| 2020 | 132.0 | 13 |
| 2025 | 147.9 | 4 |

## Interpretation

The harmonised index avoids the large composition jumps of the summed-output level measure. It rises by about **48%** from 2000 to 2025, suggesting increasing cutoff-institution output per Commission/judicial position.

This is still not a completed overproduction test:

- institutional output measures differ — degrees, graduates, enrolment, examined candidates, first-examination passes;
- the number of contributing series varies from 4 to 13;
- the judicial denominator is held constant at 92;
- the index measures growth in rates, not the absolute number of qualified aspirants.

The result is therefore a **candidate trend**, not a demonstrated overproduction result.

File: `data/analysis/gating_cutoff5_chained_harmonised.csv`.

# Balanced panel extended to 1990

The fixed five-institution panel cannot start before 2010 because Cologne’s first-examination series starts in 2010. A longer balanced panel is possible by dropping Cologne and Tartu and using four institutions with continuous data:

- College of Europe
- Harvard LL.M.
- Stockholm University
- Georgetown University

Window: **1990–2024**, fixed `n=4`.

![Balanced 1990 panel](assets/papers/methodology/gating-balanced-1990-panel.png)

\[
\frac{\sum_{i=1}^{4}\text{output}_{i,t}}
{\text{Commission posts}_t + \text{judicial positions}_t}
\times 1000
\]

- 1990: **301.2**
- 2000: **352.8**
- 2010: **486.9**
- 2020: **608.8**
- 2024: **646.2**

Sources:
- College of Europe: matriculation
- Harvard: LL.M. degrees
- Stockholm: degrees/examinations (SCB table TAB1112)
- Georgetown: degrees awarded (IPEDS; 2020 repeats 2019 and 2024 from Georgetown Key Facts)

This is a balanced panel, but still mixes output measures. It supports a **candidate trend** of rising output per Commission/judicial position, not a completed overproduction test.

File: `data/analysis/gating_balanced_1990_panel.csv`.

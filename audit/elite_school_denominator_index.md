# Gating-school output divided by elite-position denominators

## Construction

For each gating institution \(i\), benchmark year \(t\), and denominator \(k\):

\[
r_{i,k,t} = \frac{E_{i,t}}{D_{k,t}}
\]

where \(E_{i,t}\) is the institution's output and \(D_{k,t}\) is one of:

- A: Commission establishment-plan posts
- B: bar-admitted lawyers in Germany, France, Italy
- C: listed-company board seats in Germany, France, Italy
- A+B+C: aggregate denominator

For each denominator, the index is a **chained median** of five-year growth in \(r\):

\[
g_{k,t} = \operatorname{median}_{i \in S_t}\left[\frac{1}{5}\log\left(\frac{r_{i,k,t}}{r_{i,k,t-5}}\right)\right]
\]

\[
I_{k,t} = 100 \times \exp\left(5\sum_{s \le t} g_{k,s}\right)
\]

Only institutions observed at both endpoints enter a five-year growth step. This avoids level jumps when a series enters or leaves.

## Results

| Year | A: Commission | B: lawyers | C: boards | A+B+C |
|---:|---:|---:|---:|---:|
| 1990 | 100.0 | 100.0 | 100.0 | 100.0 |
| 1995 | 113.2 | 91.2 | 89.0 | 93.0 |
| 2000 | 109.4 | 71.6 | 77.4 | 74.7 |
| 2005 | 113.6 | 62.9 | 114.5 | 67.9 |
| 2010 | 104.3 | 50.5 | 115.2 | 55.3 |
| 2015 | 112.9 | 46.6 | 146.4 | 51.9 |
| 2020 | 123.3 | 47.8 | 182.9 | 53.7 |
| 2025 | 126.3 | 48.6 | 206.0 | 54.6 |

- **A:** gating output per Commission post rises about **26%**.
- **B:** output per bar-admitted lawyer roughly **halves**.
- **C:** output per listed-board seat roughly **doubles**.
- **A+B+C:** output per aggregate position falls to about **55**.

## Aggregate denominator

The aggregate is:

\[
D_t = A_t + B_t + C_t
\]

and the aggregate line uses \(E_{i,t}/D_t\) directly, not an average of the three component indices.

This matters because B is about 94% of D. Averaging the A, B, and C indices would give each component equal weight and would not represent the aggregate position count. The direct ratio weights components by their counts.

If a weighted index of component growth is required, use weights \(A_t/D_t\), \(B_t/D_t\), \(C_t/D_t\) in each five-year growth step; that approximates the direct aggregate but is not identical.

## Caveats

- Output measures differ across institutions: degrees, entrants, examined candidates, and enrolled students. The index measures growth in output per denominator, not a common production level.
- B is dominated by lawyer counts; A and C are much smaller.
- The five-year panel mixes observed and estimated denominator components; see `audit/elite_position_denominator_5y.md`.

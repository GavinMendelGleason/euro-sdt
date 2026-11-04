# Core EU institutional denominator

## Definition

Annual authorised establishment-plan posts in four core EU institutions:

- European Parliament
- Council of the EU
- European Commission, excluding executive agencies
- Court of Justice of the European Union

This is **not** the entire EU institutional bureaucracy. It excludes EU agencies, the EEAS, the Economic and Social Committee, the Committee of the Regions, the Court of Auditors and other bodies.

## Source and endpoints

European Court of Auditors, *Special Report 24/2024: EU Civil Service*, Figure 4:

- 2013: **36,835** posts
- 2023: **35,465** posts

The figure reports these two labelled endpoints; it does not publish a full annual table.

## Annual construction

- Commission establishment-plan posts: interpolated from the repository's five-year all-budget A series.
- CJEU judicial positions: annual repository series.
- European Parliament + Council residual: `ECA total - Commission posts - CJEU positions`, linearly interpolated between the two ECA endpoints.

The residual is a derived component, not an observed annual EP/Council series.

## Outputs

- `data/analysis/gating_panel_vs_coe_core_positions.csv`
- `assets/papers/methodology/gating-panel-vs-coe-core-positions.png`
- `assets/papers/methodology/gating-panel-vs-coe-core-positions.svg`

## Endpoint results

| Year | Core posts | Panel per 1,000 | College per 1,000 |
|---|---:|---:|---:|
| 2013 | 36,835 | 543.56 | 12.08 |
| 2023 | 35,465 | 678.05 | 12.97 |

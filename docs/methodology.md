# Methodology

## Scope and reporting basis

The unit of observation is **one bank at one reporting date**. The current archive has 25 first-of-month snapshots from 2024-01-01 through 2026-01-01. A January 2026 balance is the closing point for analysis of calendar year 2025. It is not a January 2026 transaction volume.

Two Central Bank of the Republic of Uzbekistan (CBU) publication families are used:

1. Main indicators of commercial banks: assets, loans, capital and deposits.
2. Loans and deposits of commercial banks: individuals and legal entities.

The project uses the HTML tables published by CBU, not a transcription from search snippets. The original bytes are gzip-compressed and retained. A SHA-256 digest of the decompressed source, URL, retrieval timestamp and reporting date are stored in `data/sources.json`. These are the versions retrieved on 28 October 2026. Later source revisions are not silently applied.

Monetary fields are **nominal UZS billion**, as published. Visualizations divide by 1,000 when displaying UZS trillion. Foreign-currency balances included in CBU totals remain in their reported sum equivalent. No inflation or exchange-rate adjustment is made.

These publications are regulatory statistics. “Capital” is retained as CBU reports it; it is not substituted for IFRS equity or used to calculate a regulatory capital-adequacy ratio.

## Bank identities and ownership

`data/banks.csv` explicitly maps published names to stable bank IDs. Whitespace and casing are normalized, but fuzzy matching is not used. An unknown name fails the build and requires review.

- “Смарт банк” and “Опен банк” map to `open`. The bank's [official notice](https://openbank.uz/ru/about/announcement) confirms the name change and continuity of the legal entity.
- “Садерат банк Иран” and “Садерат банк” map to `saderat`, preserving the source-name field.
- The English display labels are presentation aliases, not a reconstruction of the historical legal name.

Ownership comes from the section of each dated CBU table: `state` is “banks with state participation”, `other` is “other banks”. The latter may include foreign-owned banks. Poytaxt Bank changes group during the sample. Group shares are therefore current-at-date statistics, not a fixed-cohort analysis. Group membership changes and bank entry/exit can affect growth comparisons.

Banks missing from a publication are not forward-filled, and a new bank's missing prior-year balance is not set to zero.

## Financial definitions

All ratios are calculated before rounding for display.

| Metric | Definition | Interpretation |
| --- | --- | --- |
| Asset market share | Bank assets / published sector assets × 100 | Share of the full sector, even after a dashboard bank filter |
| Deposit market share | Bank deposits / published sector deposits × 100 | Share of the full sector |
| Calendar YoY growth | (Value at date / value at same date one year earlier − 1) × 100 | Unavailable if the exact baseline date is missing or its value is zero |
| YoY share change | Current market share − market share one year earlier | Percentage points, not percent growth |
| Loan-to-deposit ratio | Loans / deposits × 100 | A funding-structure measure, not a liquidity requirement or safety score |
| Retail share | Individual balances / total balances × 100 | Individuals are the source's legal category; not a claim about customer activity |
| CR5 | Sum of five largest bank assets / sum of all individual-bank assets × 100 | Top five are re-ranked each month |
| HHI | Sum of squared individual-bank asset shares expressed in percent | Scale 0–10,000; no antitrust thresholds or bank-risk labels are applied |
| Indexed series | Bank balance / its first available balance × 100 | Baseline dates can differ; a zero first balance leaves the series unavailable |

CR5/HHI use the sum of individual-bank assets so the underlying shares form a complete partition. Bank market shares use the independently published sector total. These denominators can differ slightly due to rounding. Ownership group ratios are ratios of sums, not arithmetic means of individual bank ratios.

The source's rounded percentage columns are not used in calculations. **Balance-sheet stocks are never added across reporting months.**

## Validation

The offline build rejects duplicate date/bank keys, conflicting publication dates, unsupported units, unknown bank names, negative source balances, missing months and incomplete ownership sections. It verifies all source hashes before parsing.

Each of 50 publications is reconciled by metric for the total sector, the state-participation group and the other group. This gives **750 checks**:

`25 months × 3 groups × (4 overview metrics + 6 segment metrics)`.

Each source balance is published rounded to the nearest UZS billion. When N rounded individual values are compared with one independently rounded total, the mathematical maximum rounding difference is `(N + 1) / 2` billion. The build uses this bound plus a numerical epsilon. Residuals and tolerances are saved in `data/processed/quality_checks.csv`.

Further checks compare each bank's loans and deposits across the two publication families (tolerance 1 billion) and verify retail + corporate = total (tolerance 1.5 billion). Missing values remain missing. A dash is not interpreted as a zero. The included archive has no missing required monetary balances.

Tests also cover localized number parsing, source tampering, stable IDs across the rename, exact-calendar growth, zero denominators, a hand-computable HHI example, preservation of market-share denominators and interactive dashboard controls.

## Limits and follow-up questions

- Nominal changes mix volume, prices, currency effects and possible balance-sheet reclassifications.
- Aggregate balances do not reveal unique customers, payment activity, retention, arrears or transaction failures.
- Loans above deposits can reflect wholesale, foreign or government funding. This alone is not evidence of distress.
- Deposit growth is not proof of customer trust, profitability or a successful marketing campaign.
- Profitability, NPLs, maturity and currency mismatches are outside the current dataset.
- A fall in CR5/HHI describes the distribution of assets. It does not establish a causal change in competition.
- New source dates or revisions require reviewing the period labels, alias mapping and narrative. The included historical snapshot is intentionally reproducible.

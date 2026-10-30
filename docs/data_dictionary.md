# Data dictionary

## `data/processed/bank_month.csv`

Primary key: **(`date`, `bank_id`)**. One row represents a bank's balances on the reporting date.

| Column | Type | Meaning |
| --- | --- | --- |
| `date` | ISO date | First-of-month reporting date, not publication date |
| `bank_id` | string | Stable project identifier |
| `bank_name` | string | Normalized English display label |
| `source_name` | string | Name exactly as parsed from the CBU overview table |
| `ownership` | category | `state` or `other`, classified at that date |
| `assets` | number | Total assets, UZS billion |
| `loans` | number | Loans as reported by CBU, UZS billion |
| `capital` | number | Balance-sheet capital (equity), UZS billion; reconciled to the consolidated balance |
| `deposits` | number | Total deposits, UZS billion |
| `retail_loans` | number | Loans to individuals, UZS billion |
| `corporate_loans` | number | Loans to legal entities, UZS billion |
| `retail_deposits` | number | Deposits of individuals, UZS billion |
| `corporate_deposits` | number | Deposits of legal entities, UZS billion |
| `overview_url` | URL | Source publication for main indicators |
| `segments_url` | URL | Source publication for retail/corporate indicators |

No amounts are synthetic or interpolated. Nulls in derived fields are empty CSV cells and SQL `NULL`, not zero.

## Derived outputs

`bank_month_metrics.csv` includes all fact columns plus:

- `sector_assets`, `sector_deposits`: published total-sector denominator, UZS billion.
- `asset_share_pct`, `deposit_share_pct`: market shares in percent.
- `loan_to_deposit_pct`: loans/deposits in percent.
- `retail_loan_share_pct`, `retail_deposit_share_pct`: share of individuals in the bank's balances.
- `assets_yoy_pct`, `deposits_yoy_pct`, `loans_yoy_pct`: exact-calendar yearly growth rates in percent.
- `assets_yoy_change`, `deposits_yoy_change`, `loans_yoy_change`: absolute yearly changes, UZS billion.
- `asset_share_yoy_pp`, `deposit_share_yoy_pp`: yearly changes in market share, percentage points.

`sector_totals.csv` contains independently published CBU totals by date and ownership (`total`, `state`, `other`). All monetary fields use UZS billion.

`sector_month_metrics.csv` combines published sector totals with yearly growth, bank counts, CR5, HHI, the sector loan-to-deposit ratio and the state-participation asset share.

`ownership_month_metrics.csv` aggregates individual-bank values into ownership groups by date. Slight differences from the independently published group totals are retained, not silently corrected.

`concentration_metrics.csv` contains `date`, `bank_count`, `cr5_pct` and `hhi`.

`quality_checks.csv` records every published-total check: date, publication kind, ownership, metric, published total, sum of individual banks, residual (sum minus published), tolerance, missing count, status and source URL.

`build_summary.json` reports coverage, record counts, source verification and reconciliation counts. It retains the source retrieval time; rebuilding does not change it.

## Source manifest and aliases

`data/sources.json`: an array of 50 records with `date`, `kind`, `title`, `url`, `retrieved_at`, `path`, `sha256`, `unit` and `format`. Hashes cover decompressed original HTML bytes.

`data/banks.csv`: alias registry. Multiple source names may share a bank ID. A bank ID/name pair may therefore appear more than once; a normalized source name must map to one identifier.

## Database

`data/processed/banking.duckdb` is generated locally and ignored by Git. Tables: `fact_bank_month`, `sector_totals`, `sector_context`, `macro_context`. Core views: `bank_month`, `sector_month`, `ownership_month`, `concentration`. Research views have the same names as their CSV outputs below.

The app reads the committed metric CSVs. SQL users can query the generated DuckDB database after running `python -m uzbank.build`.

## Completed-research outputs

All monetary columns below use UZS billion. `_pct` denotes percent; `_pp` denotes percentage points. Comparison dates are 2025-01-01 and 2026-01-01 unless indicated otherwise.

| Output | Grain and fields |
| --- | --- |
| `sector_context.csv` | One row per comparison date. `assets`, `loans`, `deposits` and their `_fx` components; `liabilities`, `balance_capital`, `regulatory_capital`; `borrowings_leasing`, `debt_securities`, `due_resident_banks`, `due_nonresident_banks`, `due_central_bank`, `subordinated_debt`, `investment_securities`, `net_loans`; `lcr_pct`, `nsfr_pct`, `car_pct`, `high_liquidity_assets`; `maturity_total`, `demand_deposits`, `term_1_30`, `term_31_180`, `term_181_365`, `term_over_365`; derived `deposits_local`, `term_deposits`, `other_liabilities`. |
| `macro_context.json` | `year` = 2025, `cpi_dec_to_dec_pct` = 7.3, source ID/URL and attributed CBU interpretation. |
| `sector_research.csv` | Context plus `deposit_fx_share_pct`, `term_deposit_share_pct`, `deposit_liability_share_pct`, `lcr_headroom_pp`, `nsfr_headroom_pp`, `deposit_growth_pct`, `real_deposit_growth_pct`, `deposit_liability_growth_contribution_pct`. Yearly comparisons are populated at 2026-01-01. |
| `deposit_growth_bridge.csv` | Six rows: two components per `dimension` (`currency`, `customer`, `maturity`); `opening`, `closing`, `change`, `contribution_pct`. Each dimension independently decomposes total deposit growth. |
| `state_share_bridge.csv` | One 2024–2025 endpoint decomposition: opening/closing sector and state assets, `closing_fixed_state_assets`, opening/fixed-cohort/closing shares, `growth_effect_pp`, `reclassification_effect_pp`. |
| `funding_structure.csv` | Date × ownership across all 25 dates: assets, balance capital, liabilities, deposits, other liabilities, deposit/non-deposit liability shares, loan-to-deposit ratio. |
| `bank_deposit_growth.csv` | Bank × date with an exact year-ago observation: `total_change`, `individual_change`, `legal_entity_change`, `legal_entity_contribution_pct`, `sector_growth_contribution_pct`, `deposit_share_yoy_pp`. |
| `initial_top5_growth.csv` | Two fixed cohorts over 2024–2025: `initial_top5` and `outside_initial_top5`, with opening/closing assets and growth percent. |
| `research_checks.csv` | 14 controls: `date`, `check`, `actual`, `expected`, `residual`, `tolerance`, `status`. Residual = actual − expected. |

`data/research/sources.json` has six records with `source_id`, `kind`, `title`, `url`, `retrieved_at`, `path`, `sha256`. The [source guide](../data/research/README.md) maps publication kinds to extracted fields.

`build_summary.json` distinguishes 50 bank-source publications from six research publications, and 750 bank reconciliations from 14 research reconciliations. `source_publications` and `checks_passed` report the combined totals of 56 and 764.

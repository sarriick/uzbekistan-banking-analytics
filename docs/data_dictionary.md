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
| `capital` | number | CBU reported capital, UZS billion |
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

`data/processed/banking.duckdb` is generated locally and ignored by Git. Tables: `fact_bank_month`, `sector_totals`. Views: `bank_month`, `sector_month`, `ownership_month`, `concentration`.

The app reads the committed metric CSVs. SQL users can query the generated DuckDB database after running `python -m uzbank.build`.

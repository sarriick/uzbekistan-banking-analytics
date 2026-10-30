# Supplemental research evidence

Six frozen Central Bank of Uzbekistan publications complete the 2024–2025 study. `sources.json` records exact URLs, titles, retrieval times and SHA-256 hashes of decompressed original HTML. The archive was retrieved on 29 October 2026.

| Kind | Extracted evidence |
| --- | --- |
| `sector_indicators` | 2025/2026 assets, loans, deposits and their foreign-currency components |
| `balance` | 2025/2026 liabilities, balance capital and funding categories |
| `maturity` | Deposits by demand and four term buckets on both comparison dates |
| `liquidity` | LCR, NSFR, their stated minima and high-liquid-asset amounts |
| `capital_adequacy` | Regulatory capital and the reported capital-adequacy ratio |
| `monetary_policy` | 2025 year-end CPI and CBU's explanation of local-currency savings conditions |

`python -m uzbank.build` verifies the archive, parses it through `uzbank.research` and reconciles 14 controls. It then builds the SQL views in `sql/03_completed_research.sql`. The normal build is offline. The source is CBU; extracted outputs and analysis are produced by this project.

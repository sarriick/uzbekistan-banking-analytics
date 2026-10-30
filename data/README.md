# Data attribution

Source: **Central Bank of the Republic of Uzbekistan**, [banking statistics](https://cbu.uz/ru/statistics/bankstats/).

The archive contains official main-indicator and loans/deposits publications for 25 monthly reporting dates, 2024-01-01 through 2026-01-01. Original HTML bytes are stored as `.html.gz` files in `raw/`; the accompanying `sources.json` contains exact source URLs, titles, reporting dates, retrieval timestamps and SHA-256 hashes.

`processed/` CSVs are derived using the project code. They are not a separate official publication. Rounding, definitions, transformations and limitations are documented in [methodology](../docs/methodology.md).

Six additional publications in [`research/`](research/README.md) supply comparative 2025/2026 currency, maturity, liability, liquidity and regulatory-capital evidence, plus year-end CPI. The full study therefore uses **56 publications**. Each supplemental original is archived and hashed separately in `research/sources.json`.

The project's MIT license applies to original code and documentation. It does not grant a new license over CBU publications or any other third-party material. Preserve the source attribution when reusing the data.

There are no customer records, transaction-level data, credentials or private bank documents in this dataset.

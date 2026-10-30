# Methodology

## Reporting basis and evidence

One observation is one bank at one reporting date. The study covers 25 first-of-month snapshots from **2024-01-01 through 2026-01-01**, the endpoints for calendar years 2024–2025. Balances are stocks at those dates; changes compare two stocks.

The archive contains **56 CBU publications**:

- 25 main-indicator tables: bank assets, loans, balance-sheet capital and deposits.
- 25 loans/deposits tables: individuals and legal entities.
- Six supplemental publications: sector currency composition, consolidated balance, deposit maturity, liquidity, regulatory capital adequacy and the 28 January 2026 monetary-policy decision.

The six comparative sources supply **2025-01-01 and 2026-01-01** values. Their original HTML is retained in `data/research/raw/`; the monthly archive is in `data/raw/`. Both manifests record URL, retrieval timestamp and SHA-256 of the decompressed original bytes. Versions were retrieved on 28–29 October 2026 and are frozen for reproducibility. The offline build verifies hashes before parsing.

Money is in **nominal UZS billion**; charts divide by 1,000 for UZS trillion. Foreign-currency balances use CBU's reported UZS equivalents. The separately labelled real deposit-growth measure deflates the aggregate stock using CPI. The statistical perimeter is CBU commercial banks. Balance-sheet capital reconciles to the equity line of the consolidated balance; regulatory capital and the capital-adequacy ratio come from their dedicated CBU publication.

## Bank identities and ownership

`data/banks.csv` maps reviewed source aliases to stable IDs. Unknown aliases fail the build. Source labels are retained alongside normalized English display labels.

- Smart Bank and Open Bank share `open`, supported by the bank's [official name-change notice](https://openbank.uz/ru/about/announcement).
- Saderat spelling variants share `saderat`.
- `state` means CBU's banks with state participation; `other` means its other-bank group, including foreign-owned banks.

Ownership is recorded on each reporting date. Poytaxt Bank moves from `state` on 2024-09-01 to `other` on 2024-10-01. It is the only bank present at both endpoints whose group differs. Bank entry and exit remain in the actual sector perimeter. Missing bank observations are retained as missing; the build uses exact-date comparisons.

## Core metrics

Ratios use unrounded amounts before presentation rounding.

| Metric | Formula and interpretation |
| --- | --- |
| Asset / deposit market share | Bank value / independently published sector value × 100. Dashboard selections retain the full-sector denominator. |
| Calendar YoY growth | (Current / same calendar date one year earlier − 1) × 100. Missing or zero baselines return NULL. |
| Share change | Current share − year-ago share, in percentage points. |
| Loan-to-deposit ratio | Loans / deposits × 100, describing the relative sizes of these balance-sheet stocks. |
| Individual-depositor share | Individual deposits / total bank deposits × 100. |
| CR5 | Assets of the five largest banks / sum of individual-bank assets × 100; ranks are recomputed monthly. |
| HHI | Sum of squared bank asset shares in percent; scale 0–10,000. |
| Indexed balance | Balance / the bank's first available balance × 100; a zero baseline returns NULL. |

CR5 and HHI use bank sums, forming a complete partition. Market shares use published totals. The slight difference reflects source rounding. Group ratios use ratios of sums. Balances are compared across dates rather than added over time.

## Deposit-growth decomposition and inflation

Each contribution is `(component at 2026-01-01 − component at 2025-01-01) / sector deposit increase × 100`.

| Independent dimension | Components | Provenance |
| --- | --- | --- |
| Currency | Local = total − foreign; foreign in UZS equivalent | Sector indicators |
| Customer | Individuals; legal entities | Monthly segment tables |
| Maturity | Demand; term = total − demand | Deposit maturity table |

The term component includes all four dated buckets: 1–30, 31–180, 181–365 and over 365 days. These are **three separate decompositions of the same 108,566 billion UZS increase**, not a joint customer × currency × maturity cube. Contributions sum to about 100% within each dimension. The customer change sums to 108,565 billion because independently rounded beginning and ending totals differ by 1 billion. The term residual preserves the published deposit total; the January 2025 sum of rounded maturity buckets differs by 1 billion.

The December-to-December 2025 CPI increase is **7.3%**, stated in CBU's [28 January 2026 decision](https://cbu.uz/ru/monetary-policy/publications/press-releases/3368594/). Real aggregate deposit-stock growth is:

`((417258 / 308692) / 1.073 − 1) × 100 = 25.9736%`.

This measures the change in the aggregate deposit balance's purchasing power at the two dates. CBU's statement that positive real rates supported local-currency savings is reported as CBU's economic assessment. The project's numerical attribution is the directly measured component contribution.

## Liquidity, capital and funding

LCR (liquidity coverage ratio), NSFR (net stable funding ratio), high-liquid-asset amounts and the capital-adequacy ratio are read from CBU's comparative sector tables. CBU gives a **100% minimum for LCR and NSFR** in the table labels. Headroom equals the reported ratio minus 100 percentage points. These are sector aggregate results. The capital-adequacy ratio uses the separately published regulatory measure.

Group liabilities are `assets − balance-sheet capital`; non-deposit liabilities are `liabilities − deposits`. A group's deposit-funding share is `sum(deposits) / sum(liabilities) × 100`. This accounting identity establishes the actual deposit/non-deposit mix. The sector balance separately identifies borrowings and leasing, issued securities, interbank amounts and subordinated debt. The **247,691 billion UZS borrowings/leasing** amount is sector-wide; group non-deposit residuals encompass all non-deposit liability categories.

The contribution of deposits to the year's sector liability growth is `(417258 − 308692) / (789424 − 654538) × 100 = 80.4872%`.

## State-share decomposition

The sequential endpoint decomposition uses **bank-sum denominators throughout**. Let A0 and A1 be sector assets at the start and end; S0 is the opening state group, S1 is the closing state group, and F1 is closing assets of the banks classified as state at the opening date.

1. Opening share: `100 × S0 / A0 = 67.740842%`.
2. Hold initial groups fixed: `100 × F1 / A1 = 63.529113%`.
3. Apply the closing classification: `100 × S1 / A1 = 63.468881%`.

Relative balance-growth effect = step 2 − step 1 = **−4.211730 pp**. Reclassification effect = step 3 − step 2 = **−0.060232 pp**. Their sum is the actual **−4.271961 pp** change. The first component accounts for **98.6%** and the second **1.4%** of this decline. Poytaxt's ending 557 billion UZS of assets determines the second component.

This ordering holds initial ownership fixed first and applies final ownership second. The growth component includes changes across the observed sector perimeter, including entry/exit; it is a balance-change attribution. The ordering is part of the definition and is implemented explicitly in SQL.

## Concentration and bank contribution rankings

The initial top five are National Bank of Uzbekistan, SQB, Agrobank, Asakabank and Ipoteka-bank. Their membership is fixed for the **24.8% vs 64.7%** growth comparison; the outside cohort includes banks entering/exiting the observed perimeter. CR5 itself re-ranks banks at every date; Kapitalbank replaces Ipoteka-bank in the endpoint top five.

Bank deposit growth contribution divides each matched bank's absolute change by the published sector change. Deposit-share change compares full-sector shares. Octobank leads the latter, while Agrobank leads absolute growth. Rankings use banks with exact year-ago observations; all 35 banks at the final date have the required baseline. Retail leadership is ranked by the amount of deposits belonging to individuals.

## Validation and reproducibility

The build rejects invalid hashes, duplicate date/bank keys, missing months, conflicting reporting dates, unknown units/names, negative balances and incomplete ownership sections.

**750 monthly reconciliations:** `25 dates × 3 groups × (4 overview + 6 segment metrics)`. For N independently rounded bank amounts and a rounded sector total, the tolerance is `(N + 1) / 2` billion plus numerical epsilon. Residuals are in `quality_checks.csv`.

**14 supplemental reconciliations:** seven on each comparison date. Assets, loans, deposits and balance capital agree with the monthly archive; assets equal liabilities plus capital; the maturity total agrees with deposits; maturity buckets reconcile. Tolerances are 1 billion for two rounded values, 1.5 for the three-term balance identity and 3 for five rounded maturity components plus their rounded total. Results are in `research_checks.csv`.

Additional checks reconcile each bank's loans/deposits across publications (1 billion) and individual + legal-entity balances to the total (1.5 billion). Tests cover source tampering, known controls, calendar joins, zero denominators, fixed-cohort decomposition, funding identities and app interactions. GitHub Actions rebuilds both data and the research memo and verifies their agreement with committed outputs.

Run `python -m uzbank.build`, `python -m uzbank.report`, then `python -m pytest -q`. Research text is produced by one shared generator for Markdown, HTML and Streamlit.

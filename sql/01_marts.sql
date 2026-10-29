-- Source amounts are stocks at the reporting date, in UZS billion.
-- Ownership follows CBU classification at each date, not today's status.
CREATE OR REPLACE VIEW bank_month AS
SELECT b.*, s.assets AS sector_assets, s.deposits AS sector_deposits,
       100.0*b.assets/NULLIF(s.assets,0) AS asset_share_pct,
       100.0*b.deposits/NULLIF(s.deposits,0) AS deposit_share_pct,
       100.0*b.loans/NULLIF(b.deposits,0) AS loan_to_deposit_pct,
       100.0*b.retail_loans/NULLIF(b.loans,0) AS retail_loan_share_pct,
       100.0*b.retail_deposits/NULLIF(b.deposits,0) AS retail_deposit_share_pct,
       100.0*(b.assets/NULLIF(y.assets,0)-1) AS assets_yoy_pct,
       100.0*(b.deposits/NULLIF(y.deposits,0)-1) AS deposits_yoy_pct,
       100.0*(b.loans/NULLIF(y.loans,0)-1) AS loans_yoy_pct,
       b.assets-y.assets AS assets_yoy_change,
       b.deposits-y.deposits AS deposits_yoy_change,
       b.loans-y.loans AS loans_yoy_change,
       100.0*(b.assets/NULLIF(s.assets,0)-y.assets/NULLIF(sy.assets,0)) AS asset_share_yoy_pp,
       100.0*(b.deposits/NULLIF(s.deposits,0)-y.deposits/NULLIF(sy.deposits,0)) AS deposit_share_yoy_pp
FROM fact_bank_month b
JOIN sector_totals s ON b.date=s.date AND s.ownership='total'
-- Exact calendar join. A missing month must never be treated as last year.
LEFT JOIN fact_bank_month y ON b.bank_id=y.bank_id AND y.date=b.date-INTERVAL '1 year'
LEFT JOIN sector_totals sy ON sy.date=y.date AND sy.ownership='total';

CREATE OR REPLACE VIEW concentration AS
WITH ranked AS (
 SELECT date, bank_id, assets,
        ROW_NUMBER() OVER(PARTITION BY date ORDER BY assets DESC, bank_id) AS rank,
        SUM(assets) OVER(PARTITION BY date) AS bank_sum
 FROM fact_bank_month
)
SELECT date, COUNT(*) AS bank_count,
       100.0*SUM(CASE WHEN rank<=5 THEN assets ELSE 0 END)/MAX(bank_sum) AS cr5_pct,
       SUM(POWER(100.0*assets/NULLIF(bank_sum,0),2)) AS hhi
FROM ranked GROUP BY date;

CREATE OR REPLACE VIEW sector_month AS
SELECT s.*, c.bank_count, c.cr5_pct, c.hhi,
       100.0*s.loans/NULLIF(s.deposits,0) AS loan_to_deposit_pct,
       100.0*(s.assets/NULLIF(y.assets,0)-1) AS assets_yoy_pct,
       100.0*(s.deposits/NULLIF(y.deposits,0)-1) AS deposits_yoy_pct,
       100.0*(s.loans/NULLIF(y.loans,0)-1) AS loans_yoy_pct,
       100.0*g.assets/NULLIF(s.assets,0) AS state_asset_share_pct
FROM sector_totals s
JOIN concentration c USING(date)
JOIN sector_totals g ON g.date=s.date AND g.ownership='state'
LEFT JOIN sector_totals y ON y.date=s.date-INTERVAL '1 year' AND y.ownership='total'
WHERE s.ownership='total';

CREATE OR REPLACE VIEW ownership_month AS
SELECT date, ownership, COUNT(*) AS bank_count,
       SUM(assets) AS assets, SUM(loans) AS loans, SUM(deposits) AS deposits,
       SUM(retail_loans) AS retail_loans, SUM(retail_deposits) AS retail_deposits,
       100.0*SUM(loans)/NULLIF(SUM(deposits),0) AS loan_to_deposit_pct
FROM fact_bank_month GROUP BY date, ownership;

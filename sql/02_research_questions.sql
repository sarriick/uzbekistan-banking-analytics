-- Run after 01_marts.sql or against data/processed/banking.duckdb.

-- Q1. Who gained deposit market share over the latest full year?
SELECT bank_name, deposits, deposits_yoy_pct, deposit_share_pct, deposit_share_yoy_pp
FROM bank_month WHERE date=(SELECT MAX(date) FROM bank_month)
ORDER BY deposit_share_yoy_pp DESC NULLS LAST LIMIT 10;

-- Q2. Which banks contributed most to sector asset growth in the latest year?
-- Existing matched banks only. New entrants have no artificial zero baseline.
SELECT bank_name, assets_yoy_change,
       100.0*assets_yoy_change/NULLIF((
         SELECT a.assets-b.assets FROM sector_month a
         JOIN sector_month b ON b.date=a.date-INTERVAL '1 year'
         WHERE a.date=(SELECT MAX(date) FROM sector_month)),0) AS contribution_pct
FROM bank_month WHERE date=(SELECT MAX(date) FROM bank_month)
ORDER BY assets_yoy_change DESC NULLS LAST;

-- Q3. How did concentration evolve? HHI uses individual-bank shares (0..10000).
SELECT date, bank_count, cr5_pct, hhi FROM concentration ORDER BY date;

-- Q4. Who grew loans faster than deposits? This is descriptive, not a risk score.
SELECT bank_name, loans_yoy_pct, deposits_yoy_pct, loan_to_deposit_pct
FROM bank_month WHERE date=(SELECT MAX(date) FROM bank_month)
  AND loans_yoy_pct>deposits_yoy_pct
ORDER BY loans_yoy_pct-deposits_yoy_pct DESC;

-- Q5. How do retail deposit shares differ by CBU ownership group?
SELECT date, ownership, retail_deposits, deposits,
       100.0*retail_deposits/NULLIF(deposits,0) AS retail_deposit_share_pct
FROM ownership_month ORDER BY date, ownership;

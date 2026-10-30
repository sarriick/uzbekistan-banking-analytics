-- Execute after python -m uzbank.build against data/processed/banking.duckdb.
-- Each result corresponds to a completed finding in reports/findings.ru.md.

-- 1. Deposit growth by currency, customer and maturity: independent dimensions.
SELECT * FROM deposit_growth_bridge ORDER BY dimension, contribution_pct DESC;
SELECT date,deposit_growth_pct,real_deposit_growth_pct,deposit_fx_share_pct
FROM sector_research ORDER BY date;

-- 2. Aggregate liquidity buffers, stable funding and regulatory capital adequacy.
SELECT date,lcr_pct,nsfr_pct,lcr_headroom_pp,nsfr_headroom_pp,
       high_liquidity_assets,term_deposit_share_pct,car_pct
FROM sector_research ORDER BY date;

-- 3. Falling concentration and the fixed initial-top-five growth comparison.
SELECT date,bank_count,cr5_pct,hhi FROM concentration ORDER BY date;
SELECT * FROM initial_top5_growth ORDER BY cohort;

-- 4. Relative balance growth versus ownership reclassification, 2024-2025.
SELECT opening_share_pct,fixed_cohort_closing_share_pct,closing_share_pct,
       growth_effect_pp,reclassification_effect_pp FROM state_share_bridge;

-- 5. Share-gain leaders and their contribution to sector deposit growth.
SELECT bank_name,deposit_share_yoy_pp,total_change,sector_growth_contribution_pct,
       individual_change,legal_entity_change,legal_entity_contribution_pct
FROM bank_deposit_growth WHERE date=(SELECT MAX(date) FROM bank_deposit_growth)
ORDER BY deposit_share_yoy_pp DESC LIMIT 10;
SELECT bank_name,total_change,sector_growth_contribution_pct
FROM bank_deposit_growth WHERE date=(SELECT MAX(date) FROM bank_deposit_growth)
ORDER BY total_change DESC LIMIT 5;

-- 6. Liability composition: group accounting identity and sector growth funding.
SELECT * FROM funding_structure WHERE date=(SELECT MAX(date) FROM funding_structure)
ORDER BY ownership;
SELECT date,deposit_liability_share_pct,deposit_liability_growth_contribution_pct,
       borrowings_leasing,debt_securities FROM sector_research ORDER BY date;

-- 7. Ranking by individual-depositor balances at the study endpoint.
SELECT b.bank_name,b.retail_deposits,b.retail_deposit_share_pct,
       100*b.retail_deposits/s.retail_deposits AS share_of_individual_deposits_pct
FROM bank_month b JOIN sector_totals s ON b.date=s.date AND s.ownership='total'
WHERE b.date=(SELECT MAX(date) FROM bank_month)
ORDER BY b.retail_deposits DESC LIMIT 10;

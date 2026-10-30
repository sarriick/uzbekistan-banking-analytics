-- Supplemental sources and bank-level arithmetic close the research questions.
CREATE OR REPLACE VIEW sector_research AS
SELECT c.*,
       100*c.deposits_fx/c.deposits AS deposit_fx_share_pct,
       100*c.term_deposits/c.deposits AS term_deposit_share_pct,
       100*c.deposits/c.liabilities AS deposit_liability_share_pct,
       c.lcr_pct-100 AS lcr_headroom_pp,
       c.nsfr_pct-100 AS nsfr_headroom_pp,
       100*(c.deposits/y.deposits-1) AS deposit_growth_pct,
       100*((c.deposits/y.deposits)/(1+m.cpi_dec_to_dec_pct/100)-1) AS real_deposit_growth_pct,
       100*(c.deposits-y.deposits)/(c.liabilities-y.liabilities) AS deposit_liability_growth_contribution_pct
FROM sector_context c
LEFT JOIN sector_context y ON y.date=c.date-INTERVAL '1 year'
LEFT JOIN macro_context m ON m.year=YEAR(c.date)-1;

CREATE OR REPLACE VIEW deposit_growth_bridge AS
WITH dates AS (SELECT MIN(date) AS first_date, MAX(date) AS last_date FROM sector_context),
parts AS (
 SELECT c.date, 'currency' AS dimension, 'local' AS component, c.deposits_local AS amount FROM sector_context c
 UNION ALL SELECT date,'currency','foreign',deposits_fx FROM sector_context
 UNION ALL SELECT date,'maturity','term',term_deposits FROM sector_context
 UNION ALL SELECT date,'maturity','demand',demand_deposits FROM sector_context
 UNION ALL SELECT s.date,'customer','individuals',s.retail_deposits FROM sector_totals s,dates d
   WHERE s.ownership='total' AND s.date IN(d.first_date,d.last_date)
 UNION ALL SELECT s.date,'customer','legal_entities',s.corporate_deposits FROM sector_totals s,dates d
   WHERE s.ownership='total' AND s.date IN(d.first_date,d.last_date)
)
SELECT a.dimension,a.component,b.amount AS opening,a.amount AS closing,
       a.amount-b.amount AS change,
       100*(a.amount-b.amount)/(ce.deposits-cs.deposits) AS contribution_pct
FROM parts a,dates d
JOIN sector_context cs ON cs.date=d.first_date
JOIN sector_context ce ON ce.date=d.last_date
JOIN parts b ON b.date=d.first_date
WHERE a.date=d.last_date AND a.dimension=b.dimension AND a.component=b.component;

-- Sequential endpoint decomposition: first hold ownership at its initial state,
-- then apply endpoint reclassification. Both components use individual-bank sums.
CREATE OR REPLACE VIEW state_share_bridge AS
WITH dates AS (SELECT MIN(date) AS first_date, MAX(date) AS last_date FROM fact_bank_month),
base AS (SELECT f.* FROM fact_bank_month f,dates d WHERE f.date=d.first_date),
final AS (SELECT f.* FROM fact_bank_month f,dates d WHERE f.date=d.last_date),
values AS (
 SELECT (SELECT SUM(assets) FROM base) AS opening_sector_assets,
        (SELECT SUM(assets) FROM final) AS closing_sector_assets,
        (SELECT SUM(assets) FROM base WHERE ownership='state') AS opening_state_assets,
        (SELECT SUM(f.assets) FROM final f JOIN base b USING(bank_id) WHERE b.ownership='state') AS closing_fixed_state_assets,
        (SELECT SUM(assets) FROM final WHERE ownership='state') AS closing_state_assets
)
SELECT *,
       100*opening_state_assets/opening_sector_assets AS opening_share_pct,
       100*closing_fixed_state_assets/closing_sector_assets AS fixed_cohort_closing_share_pct,
       100*closing_state_assets/closing_sector_assets AS closing_share_pct,
       100*(closing_fixed_state_assets/closing_sector_assets-opening_state_assets/opening_sector_assets) AS growth_effect_pp,
       100*(closing_state_assets-closing_fixed_state_assets)/closing_sector_assets AS reclassification_effect_pp
FROM values;

CREATE OR REPLACE VIEW funding_structure AS
SELECT date,ownership,SUM(assets) AS assets,SUM(capital) AS balance_capital,
       SUM(assets-capital) AS liabilities,SUM(deposits) AS deposits,
       SUM(assets-capital-deposits) AS other_liabilities,
       100*SUM(deposits)/SUM(assets-capital) AS deposit_liability_share_pct,
       100*SUM(assets-capital-deposits)/SUM(assets-capital) AS other_liability_share_pct,
       100*SUM(loans)/SUM(deposits) AS loan_to_deposit_pct
FROM fact_bank_month GROUP BY date,ownership;

CREATE OR REPLACE VIEW bank_deposit_growth AS
SELECT b.date,b.bank_id,b.bank_name,b.deposits,
       b.deposits-y.deposits AS total_change,
       b.retail_deposits-y.retail_deposits AS individual_change,
       b.corporate_deposits-y.corporate_deposits AS legal_entity_change,
       100*(b.corporate_deposits-y.corporate_deposits)/NULLIF(b.deposits-y.deposits,0) AS legal_entity_contribution_pct,
       100*(b.deposits-y.deposits)/NULLIF(se.deposits-sy.deposits,0) AS sector_growth_contribution_pct,
       b.deposit_share_yoy_pp
FROM bank_month b
JOIN fact_bank_month y ON y.bank_id=b.bank_id AND y.date=b.date-INTERVAL '1 year'
JOIN sector_totals se ON se.date=b.date AND se.ownership='total'
JOIN sector_totals sy ON sy.date=y.date AND sy.ownership='total';

CREATE OR REPLACE VIEW initial_top5_growth AS
WITH dates AS (SELECT MIN(date) AS first_date, MAX(date) AS last_date FROM fact_bank_month),
initial_top AS (SELECT bank_id FROM fact_bank_month f,dates d WHERE f.date=d.first_date ORDER BY assets DESC,bank_id LIMIT 5),
amounts AS (
 SELECT f.date,CASE WHEN t.bank_id IS NULL THEN 'outside_initial_top5' ELSE 'initial_top5' END AS cohort,SUM(f.assets) AS assets
 FROM fact_bank_month f CROSS JOIN dates d LEFT JOIN initial_top t USING(bank_id)
 WHERE f.date IN(d.first_date,d.last_date) GROUP BY f.date,cohort
)
SELECT a.cohort,b.assets AS opening_assets,a.assets AS closing_assets,
       100*(a.assets/b.assets-1) AS growth_pct
FROM amounts a,dates d JOIN amounts b ON b.date=d.first_date
WHERE a.date=d.last_date AND a.cohort=b.cohort;

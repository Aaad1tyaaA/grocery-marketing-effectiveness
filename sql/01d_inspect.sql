-- Choose "Grocery Phase 1 - Verified" in DBeaver's editor toolbar.
SELECT check_name,CASE WHEN passed THEN 'PASS' ELSE 'FAIL' END AS result
FROM main.phase1_checks ORDER BY check_name;

SELECT 'fact_sales' AS table_name,count(*) AS rows FROM main.fact_sales
UNION ALL SELECT 'fact_promo',count(*) FROM main.fact_promo
UNION ALL SELECT 'dim_product',count(*) FROM main.dim_product
UNION ALL SELECT 'dim_household',count(*) FROM main.dim_household
UNION ALL SELECT 'dim_campaign',count(*) FROM main.dim_campaign
UNION ALL SELECT 'bridge_household_campaign',count(*) FROM main.bridge_household_campaign;

SELECT * FROM main.fact_sales LIMIT 25;

SELECT is_non_grocery,count(*) AS lines,round(sum(sales_value),2) AS sales_usd
FROM main.fact_sales GROUP BY is_non_grocery;

SELECT * FROM main.profile_transaction_summary;
SELECT * FROM main.profile_promotion_quality;
SELECT * FROM main.profile_columns WHERE null_rows>0 ORDER BY table_name,column_name;
SELECT * FROM main.profile_relationships WHERE affected_rows>0 ORDER BY check_name;
SELECT * FROM main.dim_product WHERE is_unknown_product ORDER BY product_id;
SELECT * FROM main.fact_promo WHERE has_conflicting_codes LIMIT 25;
SELECT * FROM main.daily_anomalies ORDER BY abs(robust_z) DESC;
SELECT * FROM main.basket_anomalies ORDER BY basket_value DESC LIMIT 10;
SELECT * FROM main.dim_campaign WHERE partially_observed ORDER BY campaign_id::INTEGER;

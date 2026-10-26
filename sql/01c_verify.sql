-- Every row must say PASS. The runner aborts and rolls back on any failure.
CREATE OR REPLACE TABLE phase1_checks AS
SELECT 'sales_rows_reconcile' AS check_name,
       (SELECT count(*) FROM fact_sales)=(SELECT count(*) FROM transactions WHERE NOT(quantity=0 AND sales_value=0)) AS passed
UNION ALL SELECT 'sales_money_reconciles', abs((SELECT sum(sales_value) FROM fact_sales)-(SELECT sum(sales_value) FROM transactions))<0.005
UNION ALL SELECT 'no_void_lines', NOT EXISTS(SELECT 1 FROM fact_sales WHERE quantity=0 AND sales_value=0)
UNION ALL SELECT 'free_lines_preserved', (SELECT count(*) FROM fact_sales WHERE sales_value=0 AND quantity>0)=(SELECT count(*) FROM transactions WHERE sales_value=0 AND quantity>0)
UNION ALL SELECT 'product_keys_unique', (SELECT count(*)=count(DISTINCT product_id) AND count(*) FILTER(WHERE product_id IS NULL)=0 FROM dim_product)
UNION ALL SELECT 'household_keys_unique', (SELECT count(*)=count(DISTINCT household_id) AND count(*) FILTER(WHERE household_id IS NULL)=0 FROM dim_household)
UNION ALL SELECT 'campaign_keys_unique', (SELECT count(*)=count(DISTINCT campaign_id) AND count(*) FILTER(WHERE campaign_id IS NULL)=0 FROM dim_campaign)
UNION ALL SELECT 'sales_products_covered', NOT EXISTS(SELECT 1 FROM fact_sales f ANTI JOIN dim_product p USING(product_id))
UNION ALL SELECT 'sales_households_covered', NOT EXISTS(SELECT 1 FROM fact_sales f ANTI JOIN dim_household h USING(household_id))
UNION ALL SELECT 'promotion_rows_reconcile', (SELECT count(*) FROM fact_promo)=(SELECT unique_keys FROM profile_promotion_quality)
UNION ALL SELECT 'promotion_source_rows_reconcile', (SELECT sum(source_row_count) FROM fact_promo)=(SELECT count(*) FROM promotions)
UNION ALL SELECT 'promo_keys_unique', NOT EXISTS(SELECT 1 FROM fact_promo GROUP BY product_id,store_id,week HAVING count(*)>1)
UNION ALL SELECT 'promo_conflicts_preserved', (SELECT count(*) FROM fact_promo WHERE has_conflicting_codes)=(SELECT conflicting_keys FROM profile_promotion_quality)
UNION ALL SELECT 'no_null_grocery_flags', NOT EXISTS(SELECT 1 FROM fact_sales WHERE is_non_grocery IS NULL)
UNION ALL SELECT 'discount_formula', NOT EXISTS(SELECT 1 FROM fact_sales WHERE abs(retailer_funded_disc-retail_disc-coupon_match_disc)>0.000001 OR abs(shelf_value-sales_value-retail_disc-coupon_match_disc)>0.000001)
UNION ALL SELECT 'local_timestamp_conversion', NOT EXISTS(SELECT 1 FROM fact_sales WHERE local_ts IS DISTINCT FROM timezone('America/New_York',timezone('UTC',transaction_timestamp_utc)))
UNION ALL SELECT 'no_reversed_campaign_windows', NOT EXISTS(SELECT 1 FROM dim_campaign WHERE end_date<start_date)
UNION ALL SELECT 'demographics_coverage', (SELECT count(*) FROM dim_household WHERE has_demographics)=(SELECT count(*) FROM demographics)
UNION ALL SELECT 'household_campaign_bridge_unique', (SELECT count(*)=count(DISTINCT(household_id,campaign_id)) FROM bridge_household_campaign)
UNION ALL SELECT 'daily_sales_reconcile', abs((SELECT sum(sales) FROM daily_sales)-(SELECT sum(sales_value) FROM fact_sales WHERE NOT is_non_grocery AND local_ts::DATE BETWEEN DATE '2017-01-01' AND DATE '2017-12-31'))<0.005
UNION ALL SELECT 'anomaly_scores_finite', NOT EXISTS(SELECT 1 FROM daily_anomalies WHERE NOT isfinite(robust_z))
UNION ALL SELECT 'promo_key_fields_not_null', NOT EXISTS(SELECT 1 FROM promotions WHERE product_id IS NULL OR store_id IS NULL OR week IS NULL);

SELECT check_name,CASE WHEN passed THEN 'PASS' ELSE 'FAIL' END AS result FROM phase1_checks ORDER BY check_name;

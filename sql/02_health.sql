-- Word guide Module 2, Steps 1.2.1-1.2.4.
-- Requires the verified fact_sales model. Rebuilds derived summaries only.
CREATE OR REPLACE TABLE main.weekly_kpis AS
SELECT week,
       DATE '2017-01-02'+((week::INTEGER-2)*7) AS week_start,
       min(local_ts)::DATE AS first_observed_purchase_date,
       count(DISTINCT household_id) AS households,
       count(DISTINCT basket_id) AS baskets,
       round(sum(sales_value),2) AS sales,
       round(sum(sales_value)/nullif(count(DISTINCT basket_id),0),2) AS aov,
       round(count(DISTINCT basket_id)::DOUBLE/nullif(count(DISTINCT household_id),0),2) AS visits_per_hh,
       round(sum(retailer_funded_disc)/nullif(sum(shelf_value),0),4) AS discount_depth,
       sum(retailer_funded_disc) AS retailer_funded_discount_usd,
       sum(shelf_value) AS shelf_value_usd
FROM main.fact_sales
WHERE NOT is_non_grocery AND week>1
GROUP BY week ORDER BY week;

-- As in the guide, category ranking includes all source weeks and a $10,000 sales floor.
-- Sold-on-discount share is SHELF-VALUE weighted, not a share of units or transactions.
CREATE OR REPLACE TABLE main.category_discount AS
SELECT department,product_category,
       round(sum(sales_value),2) AS sales,
       coalesce(sum(shelf_value) FILTER(WHERE retailer_funded_disc>0),0)/nullif(sum(shelf_value),0) AS share_sold_on_discount,
       sum(retailer_funded_disc)/nullif(sum(shelf_value),0) AS discount_depth,
       count(DISTINCT household_id) AS buyers,
       sum(retailer_funded_disc) AS retailer_funded_discount_usd,
       sum(shelf_value) AS shelf_value_usd,
       coalesce(sum(shelf_value) FILTER(WHERE retailer_funded_disc>0),0) AS discounted_shelf_value_usd
FROM main.fact_sales WHERE NOT is_non_grocery
GROUP BY department,product_category
HAVING sum(sales_value)>=10000
ORDER BY share_sold_on_discount DESC;

CREATE OR REPLACE TABLE main.business_health_summary AS
SELECT round(sum(sales_value),2) AS annual_grocery_sales,
       count(DISTINCT basket_id) AS annual_grocery_baskets,
       count(DISTINCT household_id) AS annual_grocery_households,
       round(sum(shelf_value),2) AS annual_grocery_shelf_value,
       sum(retailer_funded_disc)/nullif(sum(shelf_value),0) AS annual_grocery_discount_depth,
       round(sum(sales_value) FILTER(WHERE week=1),2) AS partial_week_1_sales,
       round(sum(sales_value) FILTER(WHERE week>1),2) AS comparable_week_sales,
       round(sum(sales_value) FILTER(WHERE is_unknown_product),2) AS unclassified_product_sales
FROM main.fact_sales WHERE NOT is_non_grocery;

CREATE OR REPLACE TABLE main.business_health_checks AS
SELECT '52_comparable_weeks' AS check_name,(SELECT count(*) FROM main.weekly_kpis)=52 AS passed
UNION ALL SELECT 'weeks_2_to_53', (SELECT min(week)=2 AND max(week)=53 AND count(DISTINCT week)=52 FROM main.weekly_kpis)
UNION ALL SELECT 'weekly_sales_reconcile',abs((SELECT sum(sales) FROM main.weekly_kpis)-(SELECT sum(sales_value) FROM main.fact_sales WHERE NOT is_non_grocery AND week>1))<0.005
UNION ALL SELECT 'weekly_baskets_reconcile',(SELECT sum(baskets) FROM main.weekly_kpis)=(SELECT count(DISTINCT basket_id) FROM main.fact_sales WHERE NOT is_non_grocery AND week>1)
UNION ALL SELECT 'weekly_discount_amount_reconciles',abs((SELECT sum(retailer_funded_discount_usd) FROM main.weekly_kpis)-(SELECT sum(retailer_funded_disc) FROM main.fact_sales WHERE NOT is_non_grocery AND week>1))<0.005
UNION ALL SELECT 'weekly_shelf_value_reconciles',abs((SELECT sum(shelf_value_usd) FROM main.weekly_kpis)-(SELECT sum(shelf_value) FROM main.fact_sales WHERE NOT is_non_grocery AND week>1))<0.005
UNION ALL SELECT 'weekly_ratios_valid',NOT EXISTS(SELECT 1 FROM main.weekly_kpis WHERE discount_depth IS NULL OR discount_depth NOT BETWEEN 0 AND 1 OR households<=0 OR baskets<=0 OR aov<0)
UNION ALL SELECT 'category_ratios_valid',NOT EXISTS(SELECT 1 FROM main.category_discount WHERE share_sold_on_discount IS NULL OR share_sold_on_discount NOT BETWEEN 0 AND 1 OR discount_depth IS NULL OR discount_depth NOT BETWEEN 0 AND 1)
UNION ALL SELECT 'category_sales_floor',NOT EXISTS(SELECT 1 FROM main.category_discount WHERE sales<10000)
UNION ALL SELECT 'annual_sales_window_reconciles',(SELECT abs(annual_grocery_sales-partial_week_1_sales-comparable_week_sales)<0.005 FROM main.business_health_summary);

INSERT INTO main.business_health_checks
SELECT 'calendar_weeks_not_first_purchase_dates',NOT EXISTS(
    SELECT 1 FROM main.weekly_kpis WHERE week_start<>DATE '2017-01-02'+((week::INTEGER-2)*7)
        OR first_observed_purchase_date NOT BETWEEN week_start AND week_start+6);

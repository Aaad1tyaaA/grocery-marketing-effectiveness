-- Connect to grocery_business_health.duckdb. Run one statement with Ctrl+Enter.
-- 1. Annual grocery scope, including partial week 1.
SELECT * FROM main.business_health_summary;
-- 2. Calendar start is separate from the first recorded purchase date.
SELECT week,week_start,first_observed_purchase_date,sales,households,baskets,aov,discount_depth
FROM main.weekly_kpis ORDER BY week;
-- 3. Recorded discount dependency is not causal lift.
SELECT department,product_category,sales,share_sold_on_discount,discount_depth,buyers
FROM main.category_discount ORDER BY share_sold_on_discount DESC LIMIT 10;
-- 4. Weighted depth uses base amounts, not an average of category percentages.
SELECT sum(retailer_funded_discount_usd)/sum(shelf_value_usd) AS period_discount_depth FROM main.weekly_kpis;
-- 5. All checks must be true.
SELECT * FROM main.business_health_checks ORDER BY check_name;

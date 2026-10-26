-- Read-only source queries saved as small profiling tables. Raw tables are unchanged.
CREATE OR REPLACE TABLE profile_transaction_summary AS
SELECT count(*) AS line_items, count(DISTINCT household_id) AS households,
       count(DISTINCT basket_id) AS baskets, count(DISTINCT store_id) AS stores,
       count(DISTINCT product_id) AS products,
       min(transaction_timestamp) AS first_timestamp_utc,
       max(transaction_timestamp) AS last_timestamp_utc,
       min(week) AS first_week, max(week) AS last_week,
       round(sum(sales_value), 2) AS sales_usd,
       count(*) FILTER (WHERE quantity=0 AND sales_value=0) AS void_lines,
       count(*) FILTER (WHERE quantity=0 AND sales_value>0) AS zero_quantity_with_sales,
       count(*) FILTER (WHERE sales_value=0 AND quantity>0) AS free_lines,
       count(*) FILTER (WHERE retail_disc>sales_value) AS discount_above_paid_price,
       count(*) FILTER (WHERE quantity>100) AS large_quantity_lines,
       max(quantity) AS maximum_quantity,
       count(*) FILTER (WHERE quantity<0 OR sales_value<0) AS negative_quantity_or_sales,
       count(*) FILTER (WHERE retail_disc<0 OR coupon_disc<0 OR coupon_match_disc<0) AS negative_discount_lines
FROM transactions;

CREATE OR REPLACE TABLE profile_missing_products AS
SELECT t.product_id, count(*) AS line_items, sum(t.sales_value) AS sales_usd
FROM transactions t ANTI JOIN products p USING(product_id)
GROUP BY t.product_id;

CREATE OR REPLACE TABLE profile_large_quantities AS
SELECT coalesce(p.department, 'UNKNOWN') AS department,
       p.product_category, count(*) AS line_items,
       max(t.quantity) AS maximum_quantity, sum(t.sales_value) AS sales_usd
FROM transactions t LEFT JOIN products p USING(product_id)
WHERE t.quantity>100 GROUP BY ALL;

CREATE OR REPLACE TABLE profile_week_boundaries AS
SELECT week, min(transaction_timestamp) AS first_timestamp_utc,
       max(transaction_timestamp) AS last_timestamp_utc,
       min(timezone('America/New_York', timezone('UTC', transaction_timestamp))) AS first_timestamp_eastern,
       max(timezone('America/New_York', timezone('UTC', transaction_timestamp))) AS last_timestamp_eastern,
       count(DISTINCT timezone('America/New_York', timezone('UTC', transaction_timestamp))::DATE) AS observed_local_dates
FROM transactions GROUP BY week;

CREATE OR REPLACE TABLE profile_campaign_windows AS
SELECT *, start_date < DATE '2017-01-01' OR end_date > DATE '2017-12-31' AS partially_observed,
       end_date < start_date AS invalid_window
FROM campaign_descriptions;

-- Duplicate rows beyond the first per product/store/week, with conflicts distinguished.
CREATE OR REPLACE TABLE profile_promotion_quality AS
WITH keys AS (
    SELECT product_id,store_id,week,count(*) AS source_rows,
           min(display_location)<>max(display_location) AS display_conflict,
           min(mailer_location)<>max(mailer_location) AS mailer_conflict
    FROM promotions GROUP BY product_id,store_id,week
)
SELECT sum(source_rows)::BIGINT AS raw_rows, count(*) AS unique_keys,
       sum(source_rows-1)::BIGINT AS extra_rows,
       count(*) FILTER(WHERE source_rows>1) AS repeated_keys,
       count(*) FILTER(WHERE display_conflict OR mailer_conflict) AS conflicting_keys
FROM keys;

CREATE OR REPLACE TABLE profile_relationships AS
SELECT 'campaigns_without_description' AS check_name, count(*) AS affected_rows
FROM campaigns c ANTI JOIN campaign_descriptions d USING(campaign_id)
UNION ALL SELECT 'campaigns_without_purchasing_household', count(*)
FROM campaigns c ANTI JOIN (SELECT DISTINCT household_id FROM transactions) h USING(household_id)
UNION ALL SELECT 'redemptions_without_campaign', count(*)
FROM coupon_redemptions r ANTI JOIN campaign_descriptions d USING(campaign_id)
UNION ALL SELECT 'redemptions_without_coupon_campaign_pair', count(*)
FROM coupon_redemptions r ANTI JOIN (SELECT DISTINCT coupon_upc,campaign_id FROM coupons) c USING(coupon_upc,campaign_id)
UNION ALL SELECT 'coupons_without_product', count(*)
FROM coupons c ANTI JOIN products p USING(product_id)
UNION ALL SELECT 'promotions_without_product', count(*)
FROM promotions m ANTI JOIN products p USING(product_id)
UNION ALL SELECT 'duplicate_household_campaign_assignments', count(*)-count(DISTINCT(household_id,campaign_id)) FROM campaigns;

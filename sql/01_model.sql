-- Rebuild derived tables only. The eight source tables are preserved.
-- The runner wraps this file in a transaction; in DBeaver run BEGIN first and COMMIT after verification.
CREATE OR REPLACE TABLE dim_product AS
SELECT *, false AS is_unknown_product FROM products
UNION ALL
SELECT DISTINCT t.product_id, NULL AS manufacturer_id, 'UNKNOWN' AS department,
       NULL AS brand, NULL AS product_category, NULL AS product_type, NULL AS package_size,
       true AS is_unknown_product
FROM transactions t ANTI JOIN products p USING(product_id);

CREATE OR REPLACE TABLE fact_sales AS
SELECT t.household_id, t.store_id, t.basket_id, t.product_id, t.week,
       t.transaction_timestamp AS transaction_timestamp_utc,
       timezone('America/New_York', timezone('UTC', t.transaction_timestamp)) AS local_ts,
       t.quantity, t.sales_value, t.retail_disc, t.coupon_disc, t.coupon_match_disc,
       t.sales_value+t.retail_disc+t.coupon_match_disc AS shelf_value,
       t.retail_disc+t.coupon_match_disc AS retailer_funded_disc,
       p.department,p.product_category,p.is_unknown_product,
       coalesce(p.department IN ('FUEL','MISCELLANEOUS'),false)
          OR coalesce(p.product_category='COUPON/MISC ITEMS',false) AS is_non_grocery
FROM transactions t JOIN dim_product p USING(product_id)
WHERE NOT(t.quantity=0 AND t.sales_value=0);

CREATE OR REPLACE TABLE fact_promo AS
SELECT product_id,store_id,week,
       bool_or(display_location<>'0') AS on_display,
       bool_or(mailer_location<>'0') AS in_mailer,
       -- Conflicting codes are explicit rather than a fabricated display/mailer pair.
       CASE WHEN min(display_location)<>max(display_location) THEN 'MULTIPLE' ELSE min(display_location) END AS display_location,
       CASE WHEN min(mailer_location)<>max(mailer_location) THEN 'MULTIPLE' ELSE min(mailer_location) END AS mailer_location,
       count(*) AS source_row_count,
       coalesce(min(display_location)<>max(display_location),false)
          OR coalesce(min(mailer_location)<>max(mailer_location),false) AS has_conflicting_codes
FROM promotions GROUP BY product_id,store_id,week;

CREATE OR REPLACE TABLE dim_household AS
SELECT h.household_id,d.* EXCLUDE(household_id),
       d.household_id IS NOT NULL AS has_demographics,
       coalesce(c.n_campaigns,0) AS n_campaigns
FROM (SELECT DISTINCT household_id FROM transactions) h
LEFT JOIN demographics d USING(household_id)
LEFT JOIN (SELECT household_id,count(DISTINCT campaign_id) AS n_campaigns FROM campaigns GROUP BY household_id) c USING(household_id);

CREATE OR REPLACE TABLE dim_campaign AS
SELECT *,start_date<DATE '2017-01-01' OR end_date>DATE '2017-12-31' AS partially_observed
FROM campaign_descriptions;

CREATE OR REPLACE TABLE bridge_household_campaign AS
SELECT DISTINCT household_id,campaign_id FROM campaigns;

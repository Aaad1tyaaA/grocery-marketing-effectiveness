-- Run a statement with Ctrl+Enter, or the entire script with Alt+X in DBeaver.
SHOW TABLES;

SELECT 'transactions' AS dataset, count(*) AS rows FROM main.transactions
UNION ALL SELECT 'promotions', count(*) FROM main.promotions
UNION ALL SELECT 'campaigns', count(*) FROM main.campaigns
UNION ALL SELECT 'campaign_descriptions', count(*) FROM main.campaign_descriptions
UNION ALL SELECT 'coupons', count(*) FROM main.coupons
UNION ALL SELECT 'coupon_redemptions', count(*) FROM main.coupon_redemptions
UNION ALL SELECT 'demographics', count(*) FROM main.demographics
UNION ALL SELECT 'products', count(*) FROM main.products;

SELECT * FROM main.transactions LIMIT 25;

SELECT min(transaction_timestamp) AS first_purchase_utc,
       max(transaction_timestamp) AS last_purchase_utc,
       count(DISTINCT household_id) AS households,
       count(DISTINCT basket_id) AS baskets,
       round(sum(sales_value), 2) AS sales_usd
FROM main.transactions;

-- A safe many-to-one join: one product record per product_id.
SELECT coalesce(p.department, 'UNKNOWN') AS department,
       count(*) AS line_items, round(sum(t.sales_value), 2) AS sales_usd
FROM main.transactions t LEFT JOIN main.products p USING (product_id)
GROUP BY 1 ORDER BY sales_usd DESC;

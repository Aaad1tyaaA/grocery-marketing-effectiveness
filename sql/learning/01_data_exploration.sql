-- 1. Preview purchases
-- WHY: Understand the columns and what one row represents.
-- Each row is a product line within a shopping basket.
-- Several product lines can belong to the same basket.
-- LIMIT 10 shows a small sample; it does not change the data.
SELECT *
FROM main.transactions
LIMIT 10;


-- 2. Count purchase lines, shopping trips, and households
-- WHY: Understand the dataset's size and distinguish its units.
-- COUNT(*) counts all rows.
-- COUNT(DISTINCT ...) counts each different ID once.
-- RESULTS:
--   Purchase lines: 1,469,307
--   Shopping trips: 155,848
--   Purchasing households: 2,469
-- USE: Avoid confusing product lines with shopping trips or customers.
SELECT
    COUNT(*) AS purchase_lines,
    COUNT(DISTINCT basket_id) AS shopping_trips,
    COUNT(DISTINCT household_id) AS households
FROM main.transactions;


-- 3. Check the observation period
-- WHY: Establish the available time window before analysing trends.
-- MIN finds the earliest timestamp or smallest week number.
-- MAX finds the latest timestamp or largest week number.
-- RESULTS:
--   First purchase: 2017-01-01 11:53:26 UTC
--   Last purchase:  2018-01-01 04:01:20 UTC
--   Source weeks: 1 to 53
-- USE: Check local dates and partial weeks before comparing periods.
-- Do not assume the January 2018 UTC timestamp is a local 2018 purchase.
SELECT
    MIN(transaction_timestamp) AS first_purchase_utc,
    MAX(transaction_timestamp) AS last_purchase_utc,
    MIN(week) AS first_week,
    MAX(week) AS last_week
FROM main.transactions;


-- 4. Count possible void purchase lines
-- WHY: These rows record neither quantity nor sales.
-- WHERE filters rows before COUNT(*) counts them.
-- AND requires both conditions to be true.
-- RESULT: 8,820 lines.
-- DECISION: Exclude these when building the clean sales table.
-- This query only counts them; it does not delete anything.
SELECT
    COUNT(*) AS void_lines
FROM main.transactions
WHERE quantity = 0
  AND sales_value = 0;


-- 5. Count free purchase lines
-- WHY: Positive quantity with zero sales could reflect free items
-- or full discounts. This condition alone does not prove an error.
-- RESULT: 2,406 lines.
-- DECISION: Retain these lines in the clean model.
-- USE: Preserve recorded quantities and zero-sales purchases.
SELECT
    COUNT(*) AS free_lines
FROM main.transactions
WHERE quantity > 0
  AND sales_value = 0;


-- 6. Count zero-quantity lines with positive sales
-- WHY: These rows contribute sales, but sales / quantity is undefined.
-- RESULT: 49 lines.
-- DECISION: Retain their sales.
-- Exclude them from unit-price calculations unless a justified
-- quantity correction is available.
SELECT
    COUNT(*) AS zero_quantity_with_sales
FROM main.transactions
WHERE quantity = 0
  AND sales_value > 0;



-- 7. Count lines where the loyalty discount exceeds sales
-- WHY: Identify deep discounts that need careful interpretation.
-- A large discount alone does not prove the row is an error.
-- DECISION: Retain these lines; do not automatically delete them.
SELECT
    COUNT(*) AS discount_above_paid_price
FROM main.transactions
WHERE retail_disc > sales_value;



-- 8. Check unusually large quantities
-- WHY: Quantity may represent fuel volume or other units,
-- rather than a count of individual grocery items.
-- DECISION: Investigate product categories before removing rows.
SELECT
    COUNT(*) AS lines_above_100,
    MAX(quantity) AS largest_quantity
FROM main.transactions
WHERE quantity > 100;


-- 9. Investigate large quantities by product category
-- WHY: Understand what the quantities represent before cleaning.
-- LEFT JOIN adds product details while retaining unmatched purchases.
SELECT
    p.department,
    p.product_category,
    COUNT(*) AS large_quantity_lines,
    MAX(t.quantity) AS largest_quantity
FROM main.transactions AS t
LEFT JOIN main.products AS p
    ON t.product_id = p.product_id
WHERE t.quantity > 100
GROUP BY p.department, p.product_category
ORDER BY large_quantity_lines DESC;

-- 10. Find purchases missing product metadata
-- WHY: An ordinary INNER JOIN would silently drop these purchases.
-- DECISION: Retain their sales and label missing products UNKNOWN.
SELECT
    COUNT(*) AS purchase_lines,
    COUNT(DISTINCT t.product_id) AS missing_product_ids,
    ROUND(SUM(t.sales_value), 2) AS sales_usd
FROM main.transactions AS t
ANTI JOIN main.products AS p
    ON t.product_id = p.product_id;


-- 11. Count extra promotion rows at the intended grain
-- WHY: We need one promotion record per product, store, and week.
-- Repeated keys could multiply purchase rows when joining.
SELECT
    COUNT(*) AS promotion_rows,
    COUNT(DISTINCT (product_id, store_id, week)) AS unique_keys,
    COUNT(*) - COUNT(DISTINCT (product_id, store_id, week))
        AS extra_rows
FROM main.promotions;

-- 12. Check whether repeated promotion keys have conflicting codes
-- WHY: Repeated keys may contain different promotion information.
-- Different codes must be handled explicitly when combining rows.
SELECT COUNT(*) AS conflicting_keys
FROM (
    SELECT product_id, store_id, week
    FROM main.promotions
    GROUP BY product_id, store_id, week
    HAVING COUNT(DISTINCT display_location) > 1
        OR COUNT(DISTINCT mailer_location) > 1
) AS conflicts;



-- 13. Check demographic coverage
-- WHY: Customer analysis must account for missing demographics.
-- LEFT JOIN keeps households even when their demographics are absent.
-- DECISION: Keep missing attributes unknown; do not fill them with zero.
SELECT
    COUNT(*) AS purchasing_households,
    COUNT(d.household_id) AS with_demographics,
    COUNT(*) - COUNT(d.household_id) AS without_demographics
FROM (
    SELECT DISTINCT household_id
    FROM main.transactions
) AS h
LEFT JOIN main.demographics AS d
    ON h.household_id = d.household_id;


-- 14. Find partially observed campaigns
-- WHY: We cannot observe their entire campaign period in this dataset.
-- DECISION: Flag them for later campaign-analysis eligibility checks.
-- This query does not remove anything.
SELECT
    campaign_id,
    campaign_type,
    start_date,
    end_date
FROM main.campaign_descriptions
WHERE start_date < DATE '2017-01-01'
   OR end_date > DATE '2017-12-31'
ORDER BY start_date;
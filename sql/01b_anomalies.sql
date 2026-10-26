-- Review flags, not deletion rules. No holiday explanations are assigned automatically.
CREATE OR REPLACE TABLE daily_sales AS
SELECT local_ts::DATE AS day,dayname(local_ts) AS weekday,
       sum(sales_value) AS sales,count(DISTINCT basket_id) AS baskets
FROM fact_sales
WHERE NOT is_non_grocery AND local_ts::DATE BETWEEN DATE '2017-01-01' AND DATE '2017-12-31'
GROUP BY ALL;

CREATE OR REPLACE TABLE daily_anomalies AS
WITH medians AS (
    SELECT *,median(sales) OVER(PARTITION BY weekday) AS weekday_median FROM daily_sales
), spreads AS (
    SELECT weekday,max(weekday_median) AS weekday_median,
           median(abs(sales-weekday_median)) AS weekday_mad FROM medians GROUP BY weekday
), scores AS (
    SELECT d.*,s.weekday_median AS typical_for_weekday,s.weekday_mad,
           (d.sales-s.weekday_median)/nullif(1.4826*s.weekday_mad,0) AS robust_z
    FROM daily_sales d JOIN spreads s USING(weekday)
)
SELECT * FROM scores WHERE abs(robust_z)>3;

CREATE OR REPLACE TABLE basket_anomalies AS
WITH baskets AS (
    SELECT basket_id,household_id,min(local_ts) AS ts,sum(sales_value) AS basket_value,count(*) AS lines
    FROM fact_sales WHERE NOT is_non_grocery GROUP BY basket_id,household_id
), cutoff AS (SELECT quantile_cont(basket_value,0.999) AS threshold FROM baskets)
SELECT b.*,c.threshold FROM baskets b CROSS JOIN cutoff c WHERE b.basket_value>c.threshold;

-- Empty or missing dates are reported without assuming a reason such as store closure.
CREATE OR REPLACE TABLE profile_missing_days AS
SELECT calendar.day::DATE AS day
FROM generate_series(DATE '2017-01-01',DATE '2017-12-31',INTERVAL 1 DAY) calendar(day)
ANTI JOIN daily_sales d ON calendar.day::DATE=d.day;

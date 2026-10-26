-- Word guide Module 3, Steps 1.3.1-1.3.5.
-- Segments use grocery purchases; cohort retention intentionally uses all clean purchases, as in the guide.
CREATE OR REPLACE TABLE main.hh_metrics AS
SELECT household_id,
       DATE '2017-12-31'-max(local_ts)::DATE AS recency_days,
       count(DISTINCT basket_id) AS baskets,
       round(sum(sales_value),2) AS spend,
       round(sum(retailer_funded_disc)/nullif(sum(shelf_value),0),3) AS discount_share,
       coalesce(round(sum(sales_value) FILTER(WHERE week BETWEEN 2 AND 27),2),0) AS spend_h1,
       coalesce(round(sum(sales_value) FILTER(WHERE week BETWEEN 28 AND 53),2),0) AS spend_h2,
       coalesce(round(sum(sales_value) FILTER(WHERE week=1),2),0) AS spend_partial_week_1
FROM main.fact_sales WHERE NOT is_non_grocery
GROUP BY household_id;

CREATE OR REPLACE TABLE main.customer_cutoffs AS
SELECT quantile_cont(spend,0.75) AS spend_p75,
       quantile_cont(spend,0.50) AS spend_p50,
       quantile_cont(baskets,0.75) AS baskets_p75,
       quantile_cont(discount_share,0.75) AS discount_p75
FROM main.hh_metrics;

CREATE OR REPLACE TABLE main.hh_segments AS
SELECT m.*,
       CASE WHEN recency_days>60 THEN '5 Lapsed'
            WHEN spend>=spend_p75 AND baskets>=baskets_p75 THEN '1 Champions'
            WHEN spend>=spend_p50 THEN '2 Loyal regulars'
            WHEN baskets>=12 THEN '3 Light regulars'
            ELSE '4 Occasional' END AS segment,
       discount_share>=discount_p75 AS deal_driven,
       CASE WHEN spend_h1=0 AND spend_h2=0 THEN 'Only partial week 1 or zero spend'
            WHEN spend_h1=0 THEN 'New in H2'
            WHEN spend_h2=0 THEN 'Gone in H2'
            WHEN spend_h2>=1.2*spend_h1 THEN 'Growing'
            WHEN spend_h2<=0.8*spend_h1 THEN 'Declining'
            ELSE 'Stable' END AS trajectory
FROM main.hh_metrics m CROSS JOIN main.customer_cutoffs;

CREATE OR REPLACE TABLE main.customer_segment_summary AS
SELECT segment,count(*) AS households,sum(spend) AS spend,
       sum(spend)/nullif((SELECT sum(spend) FROM main.hh_segments),0) AS value_share,
       avg(baskets) AS avg_baskets
FROM main.hh_segments GROUP BY segment ORDER BY segment;

CREATE OR REPLACE TABLE main.customer_trajectory_summary AS
SELECT trajectory,count(*) AS households,
       count(*)::DOUBLE/(SELECT count(*) FROM main.hh_segments) AS household_share,
       sum(spend_h1) AS spend_h1,sum(spend_h2) AS spend_h2,
       sum(spend_h2)-sum(spend_h1) AS spend_change
FROM main.hh_segments GROUP BY trajectory ORDER BY households DESC;

-- Fill elapsed months with zero activity; omit future months beyond December 2017.
-- Cohort is FIRST OBSERVED month, not a proven acquisition month in this shopper panel.
CREATE OR REPLACE TABLE main.cohort_retention AS
WITH activity AS (
    SELECT DISTINCT household_id,date_trunc('month',local_ts)::DATE AS month
    FROM main.fact_sales
    WHERE local_ts>=TIMESTAMP '2017-01-01' AND local_ts<TIMESTAMP '2018-01-01'
), first_observed AS (
    SELECT household_id,min(month) AS cohort FROM activity GROUP BY household_id
), cohort_sizes AS (
    SELECT cohort,count(*) AS cohort_size FROM first_observed GROUP BY cohort
), observed AS (
    SELECT f.cohort,datediff('month',f.cohort,a.month) AS months_since_first,
           count(*) AS active
    FROM activity a JOIN first_observed f USING(household_id) GROUP BY 1,2
)
SELECT c.cohort,r.months_since_first,c.cohort_size,coalesce(o.active,0) AS active,
       coalesce(o.active,0)::DOUBLE/c.cohort_size AS retention
FROM cohort_sizes c
CROSS JOIN LATERAL range(0,datediff('month',c.cohort,DATE '2017-12-01')+1) r(months_since_first)
LEFT JOIN observed o USING(cohort,months_since_first)
ORDER BY cohort,months_since_first;

CREATE OR REPLACE TABLE main.income_spend AS
SELECT d.income,count(*) AS households,median(s.spend) AS median_spend,avg(s.spend) AS mean_spend,
       count(*)<30 AS small_group
FROM main.hh_segments s JOIN main.demographics d USING(household_id)
GROUP BY d.income ORDER BY median_spend;

CREATE OR REPLACE TABLE main.demographic_coverage_spend AS
SELECT h.has_demographics,count(*) AS households,
       median(s.spend) AS median_spend,avg(s.spend) AS mean_spend
FROM main.hh_segments s JOIN main.dim_household h USING(household_id)
GROUP BY h.has_demographics ORDER BY h.has_demographics;

CREATE OR REPLACE TABLE main.deal_driven_spend AS
SELECT deal_driven,count(*) AS households,avg(spend) AS mean_spend,median(spend) AS median_spend
FROM main.hh_segments GROUP BY deal_driven;

CREATE OR REPLACE TABLE main.spend_concentration AS
WITH ranked AS (
    SELECT *,row_number() OVER(ORDER BY spend DESC,household_id) AS spend_rank,
           count(*) OVER() AS total_households FROM main.hh_metrics
)
SELECT count(*) AS households,ceil(count(*)*0.2)::BIGINT AS top_20pct_households,
       sum(spend) FILTER(WHERE spend_rank<=ceil(total_households*0.2)) AS top_20pct_spend,
       sum(spend) FILTER(WHERE spend_rank<=ceil(total_households*0.2))/nullif(sum(spend),0) AS top_20pct_value_share
FROM ranked;

CREATE OR REPLACE TABLE main.customer_checks AS
SELECT 'household_keys_unique' AS check_name,(SELECT count(*)=count(DISTINCT household_id) FROM main.hh_segments) AS passed
UNION ALL SELECT 'grocery_households_reconcile',(SELECT count(*) FROM main.hh_metrics)=(SELECT count(DISTINCT household_id) FROM main.fact_sales WHERE NOT is_non_grocery)
UNION ALL SELECT 'grocery_spend_reconciles',abs((SELECT sum(spend) FROM main.hh_metrics)-(SELECT sum(sales_value) FROM main.fact_sales WHERE NOT is_non_grocery))<0.005
UNION ALL SELECT 'segment_counts_reconcile',(SELECT sum(households) FROM main.customer_segment_summary)=(SELECT count(*) FROM main.hh_metrics)
UNION ALL SELECT 'segment_value_shares_sum_to_one',abs((SELECT sum(value_share) FROM main.customer_segment_summary)-1)<0.000001
UNION ALL SELECT 'trajectory_counts_reconcile',(SELECT sum(households) FROM main.customer_trajectory_summary)=(SELECT count(*) FROM main.hh_metrics)
UNION ALL SELECT 'half_year_spend_reconciles',(SELECT abs(sum(spend)-sum(spend_h1)-sum(spend_h2)-sum(spend_partial_week_1))<0.005 FROM main.hh_metrics)
UNION ALL SELECT 'lapsed_precedence',NOT EXISTS(SELECT 1 FROM main.hh_segments WHERE (recency_days>60) IS DISTINCT FROM (segment='5 Lapsed'))
UNION ALL SELECT 'recency_not_negative',NOT EXISTS(SELECT 1 FROM main.hh_metrics WHERE recency_days<0)
UNION ALL SELECT 'cohort_keys_unique',(SELECT count(*)=count(DISTINCT(cohort,months_since_first)) FROM main.cohort_retention)
UNION ALL SELECT 'cohort_month_zero_is_one',NOT EXISTS(SELECT 1 FROM main.cohort_retention WHERE months_since_first=0 AND (active<>cohort_size OR retention<>1))
UNION ALL SELECT 'cohort_rates_valid',NOT EXISTS(SELECT 1 FROM main.cohort_retention WHERE retention IS NULL OR retention NOT BETWEEN 0 AND 1 OR active>cohort_size)
UNION ALL SELECT 'cohort_households_reconcile',(SELECT sum(cohort_size) FROM main.cohort_retention WHERE months_since_first=0)=(SELECT count(DISTINCT household_id) FROM main.fact_sales WHERE local_ts>=TIMESTAMP '2017-01-01' AND local_ts<TIMESTAMP '2018-01-01')
UNION ALL SELECT 'cohort_elapsed_months_complete',NOT EXISTS(SELECT 1 FROM main.cohort_retention GROUP BY cohort HAVING count(*)<>datediff('month',cohort,DATE '2017-12-01')+1)
UNION ALL SELECT 'no_future_cohort_cells',NOT EXISTS(SELECT 1 FROM main.cohort_retention WHERE months_since_first<0 OR months_since_first>datediff('month',cohort,DATE '2017-12-01'))
UNION ALL SELECT 'demographic_coverage_reconciles',(SELECT sum(households) FROM main.demographic_coverage_spend)=(SELECT count(*) FROM main.hh_metrics)
UNION ALL SELECT 'income_sample_reconciles',(SELECT sum(households) FROM main.income_spend)=(SELECT households FROM main.demographic_coverage_spend WHERE has_demographics)
UNION ALL SELECT 'deal_driven_counts_reconcile',(SELECT sum(households) FROM main.deal_driven_spend)=(SELECT count(*) FROM main.hh_metrics);

-- Word guide Module 5, Steps 1.5.1-1.5.5. Inputs are the verified phase-1 model and raw campaign tables.
CREATE OR REPLACE TABLE main.dim_week AS
SELECT week,DATE '2017-01-02'+((week::INTEGER-2)*7) AS week_start,
       min(local_ts)::DATE AS first_observed_purchase_date
FROM main.fact_sales WHERE week>1 GROUP BY week;

CREATE OR REPLACE TABLE main.hh_week AS
SELECT h.household_id,w.week,coalesce(s.spend,0) AS spend,s.spend IS NOT NULL AS active
FROM (SELECT DISTINCT household_id FROM main.fact_sales WHERE NOT is_non_grocery) h
CROSS JOIN main.dim_week w
LEFT JOIN (
    SELECT household_id,week,sum(sales_value) AS spend
    FROM main.fact_sales WHERE NOT is_non_grocery GROUP BY household_id,week
) s USING(household_id,week);

CREATE OR REPLACE TABLE main.campaign_windows AS
SELECT c.campaign_id,c.campaign_type,c.start_date,c.end_date,
       (SELECT week FROM main.dim_week WHERE c.start_date BETWEEN week_start AND week_start+6) AS start_week,
       (SELECT week FROM main.dim_week WHERE c.end_date BETWEEN week_start AND week_start+6) AS end_week
FROM main.dim_campaign c WHERE NOT c.partially_observed;

CREATE OR REPLACE TABLE main.campaign_overview AS
SELECT d.*,coalesce(a.households,0) AS households,coalesce(r.redemptions,0) AS redemptions,
       coalesce(r.redeeming_households,0) AS redeeming_households
FROM main.dim_campaign d
LEFT JOIN (SELECT campaign_id,count(DISTINCT household_id) AS households FROM main.campaigns GROUP BY campaign_id) a USING(campaign_id)
LEFT JOIN (SELECT campaign_id,count(*) AS redemptions,count(DISTINCT household_id) AS redeeming_households FROM main.coupon_redemptions GROUP BY campaign_id) r USING(campaign_id);

CREATE OR REPLACE TABLE main.campaign_roi_inputs AS
SELECT w.campaign_id,w.campaign_type,w.start_date,w.end_date,w.start_week,w.end_week,
       w.end_week-w.start_week+1 AS weeks,o.households,o.redemptions,o.redeeming_households
FROM main.campaign_windows w JOIN main.campaign_overview o USING(campaign_id)
WHERE w.campaign_type='Type A';

CREATE OR REPLACE TABLE main.coupon_amount_summary AS
SELECT count(*) AS positive_coupon_lines,avg(coupon_disc) AS average_manufacturer_coupon_line_amount,
       median(coupon_disc) AS median_manufacturer_coupon_line_amount
FROM main.fact_sales WHERE coupon_disc>0;

-- Whole source weeks approximate date boundaries. Campaign 13 starts on Tuesday.
CREATE OR REPLACE TABLE main.campaign_window_audit AS
SELECT w.campaign_id,w.start_date,w.end_date,w.start_week,w.end_week,
       a.week_start AS weekly_start_date,b.week_start+6 AS weekly_end_date,
       datediff('day',w.start_date,w.end_date)+1 AS campaign_calendar_days,
       (w.end_week-w.start_week+1)*7 AS modeled_calendar_days,
       datediff('day',a.week_start,w.start_date) AS extra_days_before_start,
       datediff('day',w.end_date,b.week_start+6) AS extra_days_after_end,
       round(coalesce(sum(f.sales_value) FILTER(
           WHERE f.local_ts::DATE<w.start_date OR f.local_ts::DATE>w.end_date),0),2)
           AS off_date_grocery_sales_all_households
FROM main.campaign_windows w
JOIN main.dim_week a ON w.start_week=a.week
JOIN main.dim_week b ON w.end_week=b.week
LEFT JOIN main.fact_sales f ON f.week BETWEEN w.start_week AND w.end_week AND NOT f.is_non_grocery
WHERE w.campaign_type='Type A'
GROUP BY ALL;

CREATE OR REPLACE TABLE main.campaign_checks AS
SELECT 'household_week_grain_unique' AS check_name,(SELECT count(*)=count(DISTINCT(household_id,week)) FROM main.hh_week) AS passed
UNION ALL SELECT 'household_week_size',(SELECT count(*) FROM main.hh_week)=(SELECT count(DISTINCT household_id) FROM main.fact_sales WHERE NOT is_non_grocery)*(SELECT count(*) FROM main.dim_week)
UNION ALL SELECT '52_week_rows_per_household',NOT EXISTS(SELECT 1 FROM main.hh_week GROUP BY household_id HAVING count(*)<>52)
UNION ALL SELECT 'week_keys_unique',(SELECT count(*)=52 AND count(*)=count(DISTINCT week) AND min(week)=2 AND max(week)=53 FROM main.dim_week)
UNION ALL SELECT 'weekly_sales_reconcile',abs((SELECT sum(spend) FROM main.hh_week)-(SELECT sum(sales_value) FROM main.fact_sales WHERE NOT is_non_grocery AND week>1))<0.005
UNION ALL SELECT 'spend_nonnegative',NOT EXISTS(SELECT 1 FROM main.hh_week WHERE spend<0 OR spend IS NULL)
UNION ALL SELECT 'campaign_keys_unique',(SELECT count(*)=27 AND count(*)=count(DISTINCT campaign_id) FROM main.campaign_overview)
UNION ALL SELECT 'recipient_counts_reconcile',(SELECT sum(households) FROM main.campaign_overview)=(SELECT count(DISTINCT(campaign_id,household_id)) FROM main.campaigns)
UNION ALL SELECT 'redemptions_reconcile',(SELECT sum(redemptions) FROM main.campaign_overview)=(SELECT count(*) FROM main.coupon_redemptions)
UNION ALL SELECT 'selected_campaign_windows_present',(SELECT count(*) FROM main.campaign_windows WHERE campaign_type='Type A' AND start_week>=20 AND end_week<=53)=3
UNION ALL SELECT 'selected_window_dates_mapped',NOT EXISTS(SELECT 1 FROM main.campaign_roi_inputs WHERE campaign_id IN('8','13','18') AND (start_week IS NULL OR end_week IS NULL OR start_week>end_week));

INSERT INTO main.campaign_checks
SELECT 'week_starts_follow_source_calendar',NOT EXISTS(
    SELECT 1 FROM main.dim_week WHERE week_start<>DATE '2017-01-02'+((week::INTEGER-2)*7))
UNION ALL SELECT 'source_week_local_dates_consistent',NOT EXISTS(
    SELECT 1 FROM main.fact_sales f JOIN main.dim_week w USING(week)
    WHERE f.local_ts::DATE NOT BETWEEN w.week_start AND w.week_start+6)
UNION ALL SELECT 'window_approximations_accounted',NOT EXISTS(
    SELECT 1 FROM main.campaign_window_audit WHERE extra_days_before_start<0 OR extra_days_after_end<0
    OR modeled_calendar_days<>campaign_calendar_days+extra_days_before_start+extra_days_after_end);

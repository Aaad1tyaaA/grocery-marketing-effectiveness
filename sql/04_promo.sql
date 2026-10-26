-- Word guide Module 4, Steps 1.4.1-1.4.4.
-- Inputs: verified main.fact_sales and raw main.promotions.
-- Primary analysis reproduces the guide's assumption: absent promotion row = no recorded promotion.
CREATE OR REPLACE TABLE main.psw_sales AS
SELECT product_id,store_id,week,sum(quantity) AS units
FROM main.fact_sales WHERE NOT is_non_grocery AND week BETWEEN 2 AND 53
GROUP BY product_id,store_id,week;

CREATE OR REPLACE TABLE main.pairs AS
SELECT product_id,store_id FROM main.psw_sales
GROUP BY product_id,store_id HAVING count(*)>=8;

-- Aggregate only the eligible pairs instead of grouping all 21m source rows.
CREATE OR REPLACE TABLE main.panel_promotions AS
SELECT m.product_id,m.store_id,m.week,
       bool_or(m.display_location<>'0') AS on_display,
       bool_or(m.mailer_location<>'0') AS in_mailer,
       CASE WHEN min(m.display_location)<>max(m.display_location) THEN 'MULTIPLE' ELSE min(m.display_location) END AS display_location,
       CASE WHEN min(m.mailer_location)<>max(m.mailer_location) THEN 'MULTIPLE' ELSE min(m.mailer_location) END AS mailer_location,
       count(*) AS source_row_count,
       min(m.display_location)<>max(m.display_location) OR min(m.mailer_location)<>max(m.mailer_location) AS has_conflicting_codes
FROM main.promotions m SEMI JOIN main.pairs p USING(product_id,store_id)
WHERE week BETWEEN 2 AND 53 GROUP BY m.product_id,m.store_id,m.week;

CREATE OR REPLACE TABLE main.promo_panel AS
SELECT p.product_id,p.store_id,w.week,coalesce(s.units,0) AS units,
       coalesce(f.on_display,false) AS on_display,coalesce(f.in_mailer,false) AS in_mailer,
       coalesce(f.display_location,'UNOBSERVED') AS display_location,
       coalesce(f.mailer_location,'UNOBSERVED') AS mailer_location,
       f.product_id IS NOT NULL AS promo_observed,
       coalesce(f.has_conflicting_codes,false) AS has_conflicting_codes
FROM main.pairs p CROSS JOIN range(2,54) w(week)
LEFT JOIN main.psw_sales s USING(product_id,store_id,week)
LEFT JOIN main.panel_promotions f USING(product_id,store_id,week);

CREATE OR REPLACE TABLE main.promo_panel_flags AS
SELECT *,on_display OR in_mailer AS promoted,
       coalesce(lag(on_display OR in_mailer) OVER w,false) AND NOT(on_display OR in_mailer) AS week_after,
       coalesce(lag(on_display OR in_mailer,2) OVER w,false) AS two_back,
       coalesce(lag(promo_observed) OVER w,false) AS previous_promo_observed
FROM main.promo_panel
WINDOW w AS(PARTITION BY product_id,store_id ORDER BY week);

CREATE OR REPLACE TABLE main.pair_baseline AS
SELECT product_id,store_id,avg(units) AS base_units,count(*) AS base_weeks
FROM main.promo_panel_flags WHERE NOT promoted AND NOT week_after
GROUP BY product_id,store_id HAVING count(*)>=4;

CREATE OR REPLACE TABLE main.promo_lift AS
SELECT CASE WHEN on_display AND in_mailer THEN 'Display + mailer'
            WHEN on_display THEN 'Display only'
            WHEN in_mailer THEN 'Mailer only'
            WHEN week_after THEN 'Week after a promotion'
            ELSE 'No promotion' END AS condition,
       count(*) AS pair_weeks,sum(f.units) AS observed_units,sum(b.base_units) AS expected_baseline_units,
       sum(f.units)/nullif(sum(b.base_units),0) AS lift_index
FROM main.promo_panel_flags f JOIN main.pair_baseline b USING(product_id,store_id)
GROUP BY 1 ORDER BY lift_index DESC;

CREATE OR REPLACE TABLE main.display_lift AS
SELECT display_location AS placement_code,count(*) AS pair_weeks,
       sum(f.units) AS observed_units,sum(b.base_units) AS expected_baseline_units,
       sum(f.units)/nullif(sum(b.base_units),0) AS lift_index,count(*)<100 AS small_group
FROM main.promo_panel_flags f JOIN main.pair_baseline b USING(product_id,store_id)
WHERE on_display AND NOT in_mailer GROUP BY display_location ORDER BY lift_index DESC;

CREATE OR REPLACE TABLE main.promo_lift_positive_baseline AS
SELECT CASE WHEN on_display AND in_mailer THEN 'Display + mailer'
            WHEN on_display THEN 'Display only'
            WHEN in_mailer THEN 'Mailer only'
            WHEN week_after THEN 'Week after a promotion'
            ELSE 'No promotion' END AS condition,
       count(*) AS pair_weeks,sum(f.units) AS observed_units,sum(b.base_units) AS expected_baseline_units,
       sum(f.units)/nullif(sum(b.base_units),0) AS lift_index
FROM main.promo_panel_flags f JOIN main.pair_baseline b USING(product_id,store_id)
WHERE b.base_units>0 GROUP BY 1 ORDER BY lift_index DESC;

CREATE OR REPLACE TABLE main.mailer_lift AS
SELECT mailer_location AS placement_code,count(*) AS pair_weeks,
       sum(f.units) AS observed_units,sum(b.base_units) AS expected_baseline_units,
       sum(f.units)/nullif(sum(b.base_units),0) AS lift_index,count(*)<100 AS small_group
FROM main.promo_panel_flags f JOIN main.pair_baseline b USING(product_id,store_id)
WHERE in_mailer AND NOT on_display GROUP BY mailer_location ORDER BY lift_index DESC;

CREATE OR REPLACE TABLE main.post_promo_lift AS
SELECT CASE WHEN promoted THEN 'Promoted'
            WHEN week_after AND NOT two_back THEN 'Week after a single-week promotion'
            WHEN week_after THEN 'Week after a multi-week promotion'
            ELSE 'Normal' END AS condition,
       count(*) AS pair_weeks,sum(f.units) AS observed_units,sum(b.base_units) AS expected_baseline_units,
       sum(f.units)/nullif(sum(b.base_units),0) AS lift_index,
       count(*) FILTER(WHERE f.week<4) AS boundary_history_incomplete_rows
FROM main.promo_panel_flags f JOIN main.pair_baseline b USING(product_id,store_id)
GROUP BY 1 ORDER BY condition;

-- Sensitivity: retain only pair-weeks with observed promotion metadata in this and the prior week.
-- Rebuild baselines within that stricter population; this is a different estimand/sample.
CREATE OR REPLACE TABLE main.observed_pair_baseline AS
SELECT product_id,store_id,avg(units) AS base_units,count(*) AS base_weeks
FROM main.promo_panel_flags
WHERE promo_observed AND previous_promo_observed AND NOT promoted AND NOT week_after
GROUP BY product_id,store_id HAVING count(*)>=4;

CREATE OR REPLACE TABLE main.promo_lift_observed_only AS
SELECT CASE WHEN on_display AND in_mailer THEN 'Display + mailer'
            WHEN on_display THEN 'Display only'
            WHEN in_mailer THEN 'Mailer only'
            WHEN week_after THEN 'Week after a promotion'
            ELSE 'No promotion' END AS condition,
       count(*) AS pair_weeks,sum(f.units) AS observed_units,sum(b.base_units) AS expected_baseline_units,
       sum(f.units)/nullif(sum(b.base_units),0) AS lift_index
FROM main.promo_panel_flags f JOIN main.observed_pair_baseline b USING(product_id,store_id)
WHERE promo_observed AND previous_promo_observed
GROUP BY 1 ORDER BY lift_index DESC;

CREATE OR REPLACE TABLE main.promotion_coverage AS
SELECT count(*) AS pair_weeks,count(*) FILTER(WHERE promo_observed) AS observed_metadata_pair_weeks,
       count(*) FILTER(WHERE NOT promo_observed) AS missing_metadata_pair_weeks,
       count(*) FILTER(WHERE has_conflicting_codes) AS conflicting_metadata_pair_weeks,
       count(*) FILTER(WHERE promoted) AS promoted_pair_weeks,
       avg(promoted::INTEGER) AS promoted_share,
       (SELECT count(*) FROM main.pairs) AS eligible_pairs,
       (SELECT count(*) FROM main.pair_baseline) AS baseline_pairs,
       (SELECT count(*) FROM main.pair_baseline WHERE base_units=0) AS zero_unit_baseline_pairs,
       (SELECT count(*) FROM main.observed_pair_baseline) AS observed_only_baseline_pairs
FROM main.promo_panel_flags;

CREATE OR REPLACE TABLE main.promotion_checks AS
SELECT 'panel_grain_unique' AS check_name,(SELECT count(*)=count(DISTINCT(product_id,store_id,week)) FROM main.promo_panel) AS passed
UNION ALL SELECT '52_rows_per_pair',NOT EXISTS(SELECT 1 FROM main.promo_panel GROUP BY product_id,store_id HAVING count(*)<>52)
UNION ALL SELECT 'panel_size_reconciles',(SELECT count(*) FROM main.promo_panel)=52*(SELECT count(*) FROM main.pairs)
UNION ALL SELECT 'eligible_pair_history',NOT EXISTS(SELECT 1 FROM main.pairs p JOIN (SELECT product_id,store_id,count(*) AS n FROM main.psw_sales GROUP BY 1,2) s USING(product_id,store_id) WHERE n<8)
UNION ALL SELECT 'zero_fill_preserves_units',abs((SELECT sum(units) FROM main.promo_panel)-(SELECT sum(units) FROM main.psw_sales SEMI JOIN main.pairs USING(product_id,store_id)))<0.000001
UNION ALL SELECT 'promotion_aggregation_unique',(SELECT count(*)=count(DISTINCT(product_id,store_id,week)) FROM main.panel_promotions)
UNION ALL SELECT 'primary_baselines_have_four_weeks',NOT EXISTS(SELECT 1 FROM main.pair_baseline WHERE base_weeks<4)
UNION ALL SELECT 'observed_baselines_have_four_weeks',NOT EXISTS(SELECT 1 FROM main.observed_pair_baseline WHERE base_weeks<4)
UNION ALL SELECT 'condition_counts_reconcile',(SELECT sum(pair_weeks) FROM main.promo_lift)=52*(SELECT count(*) FROM main.pair_baseline)
UNION ALL SELECT 'post_condition_counts_reconcile',(SELECT sum(pair_weeks) FROM main.post_promo_lift)=(SELECT sum(pair_weeks) FROM main.promo_lift)
UNION ALL SELECT 'baseline_no_promo_index_one',(SELECT abs(lift_index-1)<0.000001 FROM main.promo_lift WHERE condition='No promotion')
UNION ALL SELECT 'primary_ratios_finite',NOT EXISTS(SELECT 1 FROM main.promo_lift WHERE lift_index IS NULL OR NOT isfinite(lift_index))
UNION ALL SELECT 'observed_ratios_finite',NOT EXISTS(SELECT 1 FROM main.promo_lift_observed_only WHERE lift_index IS NULL OR NOT isfinite(lift_index))
UNION ALL SELECT 'no_future_week_leakage',NOT EXISTS(SELECT 1 FROM main.promo_panel WHERE week<2 OR week>53)
UNION ALL SELECT 'after_promo_excludes_current_promos',NOT EXISTS(SELECT 1 FROM main.promo_panel_flags WHERE week_after AND promoted)
UNION ALL SELECT 'coverage_reconciles',(SELECT observed_metadata_pair_weeks+missing_metadata_pair_weeks=pair_weeks FROM main.promotion_coverage)
UNION ALL SELECT 'display_condition_reconciles',(SELECT sum(pair_weeks) FROM main.display_lift)=(SELECT pair_weeks FROM main.promo_lift WHERE condition='Display only')
UNION ALL SELECT 'mailer_condition_reconciles',(SELECT sum(pair_weeks) FROM main.mailer_lift)=(SELECT pair_weeks FROM main.promo_lift WHERE condition='Mailer only');

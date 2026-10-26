-- Module 5: Campaign incrementality results (run each statement with Ctrl+Enter)
-- Connect DBeaver to grocery_campaigns.duckdb first. These are compact reporting tables.

-- 1. List the Module 5 tables.
SHOW TABLES;

-- 2. Understand the 27 campaign audiences and redemption counts.
SELECT campaign_id, campaign_type, start_date, end_date, households,
       redemptions, redeeming_households
FROM main.campaign_overview
ORDER BY start_date;

-- 3. Focus on the four large Type A campaigns and see the analysis weeks.
SELECT campaign_id, start_week, end_week, weeks, households,
       redemptions, redeeming_households
FROM main.campaign_roi_inputs
ORDER BY start_week;

-- 4. Compare all four designs on the same matched support, as in the Word guide.
-- Estimates are dollars per household per week; intervals crossing zero are uncertain.
SELECT campaign_id, method, n_treated, n_control,
       round(estimate, 2) AS estimate,
       round(ci_low, 2) AS ci_low, round(ci_high, 2) AS ci_high
FROM main.guide_compatibility_estimates
WHERE campaign_id IN ('8','13','18')
ORDER BY campaign_id,
  CASE method WHEN 'naive' THEN 1 WHEN 'unmatched' THEN 2
               WHEN 'matched_pre' THEN 3 ELSE 4 END;

-- 5. Check the fake-start placebo. A lift before the real campaign warns of bias.
SELECT campaign_id, method, status, n_treated, n_control,
       round(estimate, 2) AS estimate,
       round(ci_low, 2) AS ci_low, round(ci_high, 2) AS ci_high,
       round(p_holm, 4) AS holm_adjusted_p
FROM main.placebo_tests
ORDER BY campaign_id, method;

-- 6. Inspect overlap with other campaign assignments in each analysis window.
SELECT * FROM main.campaign_overlap_audit ORDER BY campaign_id;

-- 7. See the numbers needed by the later ROI spreadsheet.
-- Costs are not observed; the last two columns prevent treating estimates as validated ROI.
SELECT * FROM main.campaign_roi_inputs ORDER BY start_week;

-- 8. Coupon amounts are line-item discounts recorded on purchases.
SELECT * FROM main.coupon_amount_summary;

-- 9. Inspect the campaign 18 weekly gap. These are pointwise intervals, not a formal trend test.
SELECT week, relative_week, during_campaign, n_treated, n_control,
       round(estimate, 2) AS gap, round(ci_low, 2) AS ci_low, round(ci_high, 2) AS ci_high
FROM main.campaign_pretrends
WHERE campaign_id='18'
ORDER BY week;

-- 10. All checks should show TRUE.
SELECT * FROM main.campaign_checks ORDER BY check_name;

-- 11. Pre-period falsification using the actual earlier-matched households and weights.
-- A nonsignificant result does not prove parallel trends.
SELECT * FROM main.pretrend_tests ORDER BY campaign_id;

-- 12. Expose source-week approximations to actual campaign dates.
-- Campaign 13's weekly outcome includes Monday 7 August, one day before its Tuesday start.
SELECT * FROM main.campaign_window_audit ORDER BY start_week;

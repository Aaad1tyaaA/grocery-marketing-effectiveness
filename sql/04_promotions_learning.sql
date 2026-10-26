-- Connect to grocery_promotions.duckdb. Run one statement with Ctrl+Enter.
-- 1. Observed panel unit indices, not causal lift.
SELECT * FROM main.promo_lift ORDER BY lift_index DESC;
-- 2. Missing metadata is treated as no recorded display/mailer in the primary scope.
SELECT * FROM main.promotion_coverage;
-- 3. This sensitivity excludes zero-baseline pairs; keep scopes separate.
SELECT * FROM main.promo_lift_positive_baseline ORDER BY lift_index DESC;
-- 4. Intentionally empty: explicit metadata supplies no nonpromotion baseline controls.
SELECT * FROM main.promo_lift_observed_only;
-- 5. Week-after patterns cannot establish stockpiling or causal lift.
SELECT * FROM main.post_promo_lift ORDER BY condition;
-- 6. The 100-pair-week presentation threshold is not a significance test.
SELECT * FROM main.display_lift WHERE NOT small_group ORDER BY lift_index DESC;
-- 7. All checks must be true.
SELECT * FROM main.promotion_checks ORDER BY check_name;

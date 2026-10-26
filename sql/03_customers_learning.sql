-- Connect to grocery_customers.duckdb. Run one statement with Ctrl+Enter.
-- 1. Grocery household segments.
SELECT * FROM main.customer_segment_summary ORDER BY segment;
-- 2. Observed spend trajectories are not forecasts of recoverable revenue.
SELECT * FROM main.customer_trajectory_summary ORDER BY households DESC;
-- 3. One row per household; these are observed patterns, not future lifetime values.
SELECT * FROM main.hh_segments ORDER BY spend DESC LIMIT 10;
-- 4. First observed purchase is not proven acquisition; future months are omitted.
SELECT * FROM main.cohort_retention ORDER BY cohort,months_since_first;
-- 5. Demographic coverage is selective.
SELECT * FROM main.demographic_coverage_spend;
-- 6. All checks must be true.
SELECT * FROM main.customer_checks ORDER BY check_name;

-- Module 6: use grocery_hillstrom.duckdb. Run ONE statement with Ctrl+Enter.
-- The calculations are already saved; these queries inspect verified outputs.

-- 1. What is randomized? Counts and outcomes per assigned customer, including zeros.
-- Why: the denominator must not depend on whether a customer bought after treatment.
SELECT * FROM main.hillstrom_arm_summary ORDER BY segment;

-- 2. Does allocation resemble the intended equal thirds? p ~ .904; warning FALSE.
-- Why: large sample ratio mismatch can indicate assignment or data-pipeline trouble.
SELECT * FROM main.hillstrom_srm;

-- 3. Are pre-email attributes reasonably balanced? Maximum absolute SMD ~ .014.
SELECT * FROM main.hillstrom_balance
ORDER BY abs(standardized_mean_difference) DESC;

-- 4. Primary six effects: rates use 0-1 units; multiply binary lifts by 100 for pp.
-- Why: compare email vs no email, not raw sales totals of slightly unequal arms.
-- CI is pointwise bootstrap; p_holm corrects six Welch tests.
SELECT arm, metric, n_treatment, n_control, treatment_mean, control_mean,
       estimate, ci_low, ci_high, p_holm
FROM main.hillstrom_effects ORDER BY arm, metric;

-- 5. Direct Men's minus Women's comparison; positive favors Men's.
-- Why: being significant against control alone does not prove one email beats another.
SELECT metric, estimate, ci_low, ci_high, p_holm
FROM main.email_head_to_head ORDER BY metric;

-- 6. Exploratory merchandise-history cuts (these labels do not identify gender).
-- Why: find hypotheses; separate subgroup p values are not interaction tests.
SELECT level, arm, metric, n_treatment, n_control, estimate, ci_low, ci_high, p_holm
FROM main.segment_effects WHERE cut='buyer' ORDER BY level, metric, arm;

-- 7. Exact quotas versus the whole-cell rule.
-- Why: whole cells select 8,486 with seed 7; boundary tie breaks fill exactly 10,000.
SELECT * FROM main.policy_audience_counts ORDER BY seed, scope, audience;

-- 8. Training-only seed 7 rules, including exact selected and suppressed counts.
-- recommended_email is a TRAINING suggestion, not a validated deployment recommendation.
SELECT cell, train_n_control, train_n_mens, train_n_womens,
       train_mens_lift, train_womens_lift, recommended_email,
       population_customers, exact_target, exact_suppress
FROM main.policy_rules WHERE seed=7 ORDER BY train_best_lift DESC;

-- 9. Does the target advantage survive a second split? It does not stay strong.
-- These overlapping splits are sensitivity checks, not independent replications.
SELECT seed, audience, n_treatment, n_control, estimate, ci_low, ci_high, p_holm
FROM main.heldout_effects
WHERE scope='exact' AND metric='spend' AND arm='Mens E-Mail'
ORDER BY seed, audience;

-- 10. Evaluate the learned per-cell VERSION mix against always sending Men's.
-- Why: a group's Men's-only lift does not evaluate its mixed version policy.
SELECT seed, audience, heldout_customers, estimate, ci_low, ci_high,
       always_mens_estimate, policy_minus_mens,
       policy_minus_mens_ci_low, policy_minus_mens_ci_high
FROM main.heldout_policy_value WHERE metric='spend' ORDER BY seed, audience;

-- 11. Check sparse spend and the number of actually observed cells (30, not 36).
SELECT * FROM main.hillstrom_profile;

-- 12. Every check should be TRUE. These verify implementation, not targeting usefulness.
SELECT * FROM main.hillstrom_checks ORDER BY check_name;

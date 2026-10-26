-- Module 6: hillstrom_input is registered from the verified CSV in source order.
CREATE OR REPLACE TABLE main.hillstrom AS
WITH features AS (
    SELECT *,CASE WHEN mens=1 AND womens=1 THEN 'both'
                  WHEN mens=1 THEN 'mens only' WHEN womens=1 THEN 'womens only' ELSE 'neither' END AS buyer,
           CASE WHEN recency<=3 THEN '1-3' WHEN recency<=8 THEN '4-8' ELSE '9-12' END AS recency_band,
           CASE WHEN history>=200 THEN 'high' ELSE 'low' END AS value_band
    FROM hillstrom_input
)
SELECT *,buyer||'|'||newbie::VARCHAR||'|'||recency_band||'|'||value_band AS cell FROM features;

CREATE OR REPLACE TABLE main.hillstrom_arm_summary AS
SELECT segment,count(*) AS customers,sum(visit) AS visitors,sum(conversion) AS buyers,
       sum(spend) AS total_spend,avg(visit) AS visit_rate,avg(conversion) AS conversion_rate,
       avg(spend) AS spend_per_assigned_customer
FROM main.hillstrom GROUP BY segment ORDER BY segment;

CREATE OR REPLACE TABLE main.hillstrom_profile AS
SELECT count(*) AS customers,count(*) FILTER(WHERE spend>0) AS positive_spenders,
       count(*) FILTER(WHERE spend=0) AS zero_spenders,max(spend) AS maximum_spend,
       sum(spend) AS total_spend,count(DISTINCT cell) AS pre_treatment_cells,
       count(*) FILTER(WHERE zip_code='Surburban') AS original_surburban_label_rows
FROM main.hillstrom;

CREATE OR REPLACE TABLE main.hillstrom_checks AS
SELECT '64000_source_rows' AS check_name,(SELECT count(*)=64000 FROM main.hillstrom) AS passed
UNION ALL SELECT 'source_row_unique',(SELECT count(*)=count(DISTINCT source_row) AND min(source_row)=1 AND max(source_row)=64000 FROM main.hillstrom)
UNION ALL SELECT 'source_fields_non_null',NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE recency IS NULL OR history_segment IS NULL OR history IS NULL OR mens IS NULL OR womens IS NULL OR zip_code IS NULL OR newbie IS NULL OR channel IS NULL OR segment IS NULL OR visit IS NULL OR conversion IS NULL OR spend IS NULL)
UNION ALL SELECT 'three_expected_arms',(SELECT count(DISTINCT segment)=3 FROM main.hillstrom) AND NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE segment NOT IN('No E-Mail','Mens E-Mail','Womens E-Mail'))
UNION ALL SELECT 'binary_flags_valid',NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE mens NOT IN(0,1) OR womens NOT IN(0,1) OR newbie NOT IN(0,1) OR visit NOT IN(0,1) OR conversion NOT IN(0,1))
UNION ALL SELECT 'recency_valid',NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE recency NOT BETWEEN 1 AND 12 OR recency<>floor(recency))
UNION ALL SELECT 'history_spend_finite_nonnegative',NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE NOT isfinite(history) OR NOT isfinite(spend) OR history<0 OR spend<0)
UNION ALL SELECT 'conversion_requires_visit',NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE conversion>visit)
UNION ALL SELECT 'positive_spend_matches_conversion',NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE (spend>0) IS DISTINCT FROM (conversion=1))
UNION ALL SELECT 'observed_feature_cells_valid',(SELECT count(DISTINCT cell) BETWEEN 1 AND 36 FROM main.hillstrom) AND NOT EXISTS(SELECT 1 FROM main.hillstrom WHERE buyer='neither')
UNION ALL SELECT 'arm_counts_reconcile',(SELECT sum(customers) FROM main.hillstrom_arm_summary)=(SELECT count(*) FROM main.hillstrom)
UNION ALL SELECT 'arm_spend_reconciles',abs((SELECT sum(total_spend) FROM main.hillstrom_arm_summary)-(SELECT sum(spend) FROM main.hillstrom))<0.000001;

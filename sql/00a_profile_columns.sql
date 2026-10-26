CREATE OR REPLACE TABLE profile_columns AS
SELECT 'transactions' AS table_name,'household_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "household_id" IS NULL) AS null_rows,count(DISTINCT "household_id") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'store_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "store_id" IS NULL) AS null_rows,count(DISTINCT "store_id") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'basket_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "basket_id" IS NULL) AS null_rows,count(DISTINCT "basket_id") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'product_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "product_id" IS NULL) AS null_rows,count(DISTINCT "product_id") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'quantity' AS column_name,'DOUBLE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "quantity" IS NULL) AS null_rows,count(DISTINCT "quantity") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'sales_value' AS column_name,'DOUBLE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "sales_value" IS NULL) AS null_rows,count(DISTINCT "sales_value") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'retail_disc' AS column_name,'DOUBLE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "retail_disc" IS NULL) AS null_rows,count(DISTINCT "retail_disc") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'coupon_disc' AS column_name,'DOUBLE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "coupon_disc" IS NULL) AS null_rows,count(DISTINCT "coupon_disc") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'coupon_match_disc' AS column_name,'DOUBLE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "coupon_match_disc" IS NULL) AS null_rows,count(DISTINCT "coupon_match_disc") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'week' AS column_name,'INTEGER' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "week" IS NULL) AS null_rows,count(DISTINCT "week") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'transactions' AS table_name,'transaction_timestamp' AS column_name,'TIMESTAMP_NS' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "transaction_timestamp" IS NULL) AS null_rows,count(DISTINCT "transaction_timestamp") AS distinct_non_null FROM "transactions"
UNION ALL
SELECT 'promotions' AS table_name,'product_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "product_id" IS NULL) AS null_rows,count(DISTINCT "product_id") AS distinct_non_null FROM "promotions"
UNION ALL
SELECT 'promotions' AS table_name,'store_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "store_id" IS NULL) AS null_rows,count(DISTINCT "store_id") AS distinct_non_null FROM "promotions"
UNION ALL
SELECT 'promotions' AS table_name,'display_location' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "display_location" IS NULL) AS null_rows,count(DISTINCT "display_location") AS distinct_non_null FROM "promotions"
UNION ALL
SELECT 'promotions' AS table_name,'mailer_location' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "mailer_location" IS NULL) AS null_rows,count(DISTINCT "mailer_location") AS distinct_non_null FROM "promotions"
UNION ALL
SELECT 'promotions' AS table_name,'week' AS column_name,'INTEGER' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "week" IS NULL) AS null_rows,count(DISTINCT "week") AS distinct_non_null FROM "promotions"
UNION ALL
SELECT 'campaigns' AS table_name,'campaign_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "campaign_id" IS NULL) AS null_rows,count(DISTINCT "campaign_id") AS distinct_non_null FROM "campaigns"
UNION ALL
SELECT 'campaigns' AS table_name,'household_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "household_id" IS NULL) AS null_rows,count(DISTINCT "household_id") AS distinct_non_null FROM "campaigns"
UNION ALL
SELECT 'campaign_descriptions' AS table_name,'campaign_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "campaign_id" IS NULL) AS null_rows,count(DISTINCT "campaign_id") AS distinct_non_null FROM "campaign_descriptions"
UNION ALL
SELECT 'campaign_descriptions' AS table_name,'campaign_type' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "campaign_type" IS NULL) AS null_rows,count(DISTINCT "campaign_type") AS distinct_non_null FROM "campaign_descriptions"
UNION ALL
SELECT 'campaign_descriptions' AS table_name,'start_date' AS column_name,'DATE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "start_date" IS NULL) AS null_rows,count(DISTINCT "start_date") AS distinct_non_null FROM "campaign_descriptions"
UNION ALL
SELECT 'campaign_descriptions' AS table_name,'end_date' AS column_name,'DATE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "end_date" IS NULL) AS null_rows,count(DISTINCT "end_date") AS distinct_non_null FROM "campaign_descriptions"
UNION ALL
SELECT 'coupons' AS table_name,'coupon_upc' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "coupon_upc" IS NULL) AS null_rows,count(DISTINCT "coupon_upc") AS distinct_non_null FROM "coupons"
UNION ALL
SELECT 'coupons' AS table_name,'product_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "product_id" IS NULL) AS null_rows,count(DISTINCT "product_id") AS distinct_non_null FROM "coupons"
UNION ALL
SELECT 'coupons' AS table_name,'campaign_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "campaign_id" IS NULL) AS null_rows,count(DISTINCT "campaign_id") AS distinct_non_null FROM "coupons"
UNION ALL
SELECT 'coupon_redemptions' AS table_name,'household_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "household_id" IS NULL) AS null_rows,count(DISTINCT "household_id") AS distinct_non_null FROM "coupon_redemptions"
UNION ALL
SELECT 'coupon_redemptions' AS table_name,'coupon_upc' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "coupon_upc" IS NULL) AS null_rows,count(DISTINCT "coupon_upc") AS distinct_non_null FROM "coupon_redemptions"
UNION ALL
SELECT 'coupon_redemptions' AS table_name,'campaign_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "campaign_id" IS NULL) AS null_rows,count(DISTINCT "campaign_id") AS distinct_non_null FROM "coupon_redemptions"
UNION ALL
SELECT 'coupon_redemptions' AS table_name,'redemption_date' AS column_name,'DATE' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "redemption_date" IS NULL) AS null_rows,count(DISTINCT "redemption_date") AS distinct_non_null FROM "coupon_redemptions"
UNION ALL
SELECT 'demographics' AS table_name,'household_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "household_id" IS NULL) AS null_rows,count(DISTINCT "household_id") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'age' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "age" IS NULL) AS null_rows,count(DISTINCT "age") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'income' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "income" IS NULL) AS null_rows,count(DISTINCT "income") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'home_ownership' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "home_ownership" IS NULL) AS null_rows,count(DISTINCT "home_ownership") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'marital_status' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "marital_status" IS NULL) AS null_rows,count(DISTINCT "marital_status") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'household_size' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "household_size" IS NULL) AS null_rows,count(DISTINCT "household_size") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'household_comp' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "household_comp" IS NULL) AS null_rows,count(DISTINCT "household_comp") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'demographics' AS table_name,'kids_count' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "kids_count" IS NULL) AS null_rows,count(DISTINCT "kids_count") AS distinct_non_null FROM "demographics"
UNION ALL
SELECT 'products' AS table_name,'product_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "product_id" IS NULL) AS null_rows,count(DISTINCT "product_id") AS distinct_non_null FROM "products"
UNION ALL
SELECT 'products' AS table_name,'manufacturer_id' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "manufacturer_id" IS NULL) AS null_rows,count(DISTINCT "manufacturer_id") AS distinct_non_null FROM "products"
UNION ALL
SELECT 'products' AS table_name,'department' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "department" IS NULL) AS null_rows,count(DISTINCT "department") AS distinct_non_null FROM "products"
UNION ALL
SELECT 'products' AS table_name,'brand' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "brand" IS NULL) AS null_rows,count(DISTINCT "brand") AS distinct_non_null FROM "products"
UNION ALL
SELECT 'products' AS table_name,'product_category' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "product_category" IS NULL) AS null_rows,count(DISTINCT "product_category") AS distinct_non_null FROM "products"
UNION ALL
SELECT 'products' AS table_name,'product_type' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "product_type" IS NULL) AS null_rows,count(DISTINCT "product_type") AS distinct_non_null FROM "products"
UNION ALL
SELECT 'products' AS table_name,'package_size' AS column_name,'VARCHAR' AS data_type,count(*) AS total_rows,count(*) FILTER(WHERE "package_size" IS NULL) AS null_rows,count(DISTINCT "package_size") AS distinct_non_null FROM "products";

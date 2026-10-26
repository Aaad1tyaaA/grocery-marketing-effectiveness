-- Optional audit query used by the generated cleaning log. It changes no tables.
SELECT 'void_lines' AS rule,count(*) AS line_items,round(sum(sales_value),2) AS sales_usd
FROM transactions WHERE quantity=0 AND sales_value=0
UNION ALL SELECT 'free_lines',count(*),round(sum(sales_value),2) FROM transactions WHERE sales_value=0 AND quantity>0
UNION ALL SELECT 'zero_quantity_with_sales',count(*),round(sum(sales_value),2) FROM transactions WHERE quantity=0 AND sales_value>0
UNION ALL SELECT 'large_quantity_lines',count(*),round(sum(sales_value),2) FROM transactions WHERE quantity>100
UNION ALL SELECT 'discount_above_paid_price',count(*),round(sum(sales_value),2) FROM transactions WHERE retail_disc>sales_value;

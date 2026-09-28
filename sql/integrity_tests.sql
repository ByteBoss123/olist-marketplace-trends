-- Each query returns the number of violating rows; every result must be 0.
select 'dim_customer pk duplicates' as test, count(*) - count(distinct customer_id) as violations from dim_customer
union all select 'dim_seller pk duplicates', count(*) - count(distinct seller_id) from dim_seller
union all select 'dim_product pk duplicates', count(*) - count(distinct product_id) from dim_product
union all select 'dim_date pk duplicates', count(*) - count(distinct date_key) from dim_date
union all select 'fact_order pk duplicates', count(*) - count(distinct order_id) from fact_order
union all select 'fact_order_item pk duplicates', count(*) - count(distinct (order_id, order_item_id)) from fact_order_item
union all select 'fact_order -> dim_customer orphans', count(*) from fact_order o where not exists (select 1 from dim_customer c where c.customer_id = o.customer_id)
union all select 'fact_order -> dim_date orphans', count(*) from fact_order o where not exists (select 1 from dim_date d where d.date_key = o.date_key)
union all select 'fact_order_item -> dim_seller orphans', count(*) from fact_order_item f where not exists (select 1 from dim_seller s where s.seller_id = f.seller_id)
union all select 'fact_order_item -> dim_product orphans', count(*) from fact_order_item f where not exists (select 1 from dim_product p where p.product_id = f.product_id)
union all select 'fact_order_item -> fact_order orphans', count(*) from fact_order_item f where not exists (select 1 from fact_order o where o.order_id = f.order_id)
union all select 'order items lost vs source', (select count(*) from src_items) - (select count(*) from fact_order_item)
union all select 'orders lost vs source', (select count(*) from src_orders) - (select count(*) from fact_order);

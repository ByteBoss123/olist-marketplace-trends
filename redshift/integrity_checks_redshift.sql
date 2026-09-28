-- Run against Amazon Redshift Serverless (workgroup default-workgroup, database dev, schema vendorpulse).
-- The Olist star schema was loaded there on 2026-08-11 by the Vendor-Pulse project.
-- Every row must return 0.
select 'dim_customer pk dup', count(*)-count(distinct customer_id) from vendorpulse.dim_customer
union all select 'dim_seller pk dup', count(*)-count(distinct seller_id) from vendorpulse.dim_seller
union all select 'dim_product pk dup', count(*)-count(distinct product_id) from vendorpulse.dim_product
union all select 'dim_date pk dup', count(*)-count(distinct date_key) from vendorpulse.dim_date
union all select 'fact_orders pk dup', count(*)-count(distinct order_id) from vendorpulse.fact_orders
union all select 'fact_order_items pk dup', count(*)-count(distinct order_id||'-'||order_item_id) from vendorpulse.fact_order_items
union all select 'orders->customer orphans', count(*) from vendorpulse.fact_orders o left join vendorpulse.dim_customer c on c.customer_id=o.customer_id where c.customer_id is null
union all select 'items->seller orphans', count(*) from vendorpulse.fact_order_items f left join vendorpulse.dim_seller x on x.seller_id=f.seller_id where x.seller_id is null
union all select 'items->product orphans', count(*) from vendorpulse.fact_order_items f left join vendorpulse.dim_product p on p.product_id=f.product_id where p.product_id is null
union all select 'items->orders orphans', count(*) from vendorpulse.fact_order_items f left join vendorpulse.fact_orders o on o.order_id=f.order_id where o.order_id is null
union all select 'orders->date orphans', count(*) from vendorpulse.fact_orders o left join vendorpulse.dim_date d on d.date_key=o.purchase_date where d.date_key is null;

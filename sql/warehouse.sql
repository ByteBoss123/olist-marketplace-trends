-- Olist star-schema KPI warehouse (DuckDB). Grain of the core fact: one row per order item.
create or replace view src_orders    as select * from read_csv_auto('data/olist_orders_dataset.csv');
create or replace view src_items     as select * from read_csv_auto('data/olist_order_items_dataset.csv');
create or replace view src_customers as select * from read_csv_auto('data/olist_customers_dataset.csv');
create or replace view src_sellers   as select * from read_csv_auto('data/olist_sellers_dataset.csv');
create or replace view src_products  as select * from read_csv_auto('data/olist_products_dataset.csv');
create or replace view src_payments  as select * from read_csv_auto('data/olist_order_payments_dataset.csv');
create or replace view src_reviews   as select * from read_csv_auto('data/olist_order_reviews_dataset.csv');
create or replace view src_cat       as select * from read_csv_auto('data/product_category_name_translation.csv');

-- Dimensions
create or replace table dim_customer as
select customer_id, customer_unique_id, customer_city, customer_state from src_customers;

create or replace table dim_seller as
select seller_id, seller_city, seller_state from src_sellers;

create or replace table dim_product as
select p.product_id,
       coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category
from src_products p left join src_cat t using (product_category_name);

create or replace table dim_date as
select distinct cast(order_purchase_timestamp as date) as date_key,
       year(order_purchase_timestamp) as year, month(order_purchase_timestamp) as month
from src_orders;

-- Facts
create or replace table fact_order as
select o.order_id, o.customer_id, cast(o.order_purchase_timestamp as date) as date_key, o.order_status,
       case when o.order_status = 'delivered' and o.order_delivered_customer_date is not null
            then (o.order_delivered_customer_date <= o.order_estimated_delivery_date)::int end as delivered_on_time,
       p.payment_value, r.review_score
from src_orders o
left join (select order_id, sum(payment_value) as payment_value from src_payments group by 1) p using (order_id)
left join (select order_id, review_score from
             (select *, row_number() over (partition by order_id order by review_answer_timestamp desc) rn from src_reviews)
           where rn = 1) r using (order_id);

create or replace table fact_order_item as
select i.order_id, i.order_item_id, i.product_id, i.seller_id, o.customer_id, o.date_key,
       i.price, i.freight_value
from src_items i join fact_order o using (order_id);

-- Self-service KPI views
create or replace view kpi_seller as
select f.seller_id, s.seller_state,
       count(distinct f.order_id) as orders, sum(f.price) as item_revenue,
       avg(o.delivered_on_time) as on_time_rate, avg(o.review_score) as avg_review
from fact_order_item f join dim_seller s using (seller_id) join fact_order o using (order_id)
group by 1, 2;

create or replace view kpi_category as
select p.category, count(distinct f.order_id) as orders, sum(f.price) as item_revenue,
       avg(o.review_score) as avg_review, avg(o.delivered_on_time) as on_time_rate
from fact_order_item f join dim_product p using (product_id) join fact_order o using (order_id)
group by 1;

create or replace view kpi_monthly as
select d.year, d.month, count(*) as orders, sum(o.payment_value) as payments,
       avg(o.delivered_on_time) as on_time_rate
from fact_order o join dim_date d using (date_key)
group by 1, 2 order by 1, 2;

-- Olist marketplace delivery trends and review-score drivers (DuckDB).
-- Late = delivered to customer after the estimated delivery date. Delivered orders only.
create or replace view orders as select * from read_csv_auto('data/olist_orders_dataset.csv');
create or replace view reviews as select * from read_csv_auto('data/olist_order_reviews_dataset.csv');

create or replace table fct_delivered_orders as
select
    order_id,
    date_trunc('month', order_purchase_timestamp) as purchase_month,
    case when order_delivered_customer_date > order_estimated_delivery_date then 1 else 0 end as is_late,
    date_diff('day', order_delivered_customer_date, order_estimated_delivery_date) as days_before_estimate
from orders
where order_status = 'delivered' and order_delivered_customer_date is not null;

-- one review per order: the latest answer
create or replace table dim_order_review as
select order_id, review_score
from (select *, row_number() over (partition by order_id order by review_answer_timestamp desc) as rn from reviews)
where rn = 1;

create or replace table agg_monthly_late_rate as
select purchase_month, count(*) as delivered_orders, avg(is_late) as late_rate
from fct_delivered_orders group by 1 order by 1;

create or replace table agg_review_by_delivery as
select is_late, count(*) as orders, avg(review_score) as avg_review,
       avg(case when review_score = 1 then 1.0 else 0 end) as one_star_share
from fct_delivered_orders join dim_order_review using (order_id)
group by 1;

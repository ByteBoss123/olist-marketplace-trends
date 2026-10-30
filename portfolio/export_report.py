"""Build Power BI CSV inputs from Olist source files, preserving order grain."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd


def build(data, output):
    data, output = Path(data), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    def read(name):
        return pd.read_csv(data / name)
    orders = read('olist_orders_dataset.csv')
    items = read('olist_order_items_dataset.csv')
    reviews = read('olist_order_reviews_dataset.csv')
    products = read('olist_products_dataset.csv')
    categories = read('product_category_name_translation.csv')
    sellers = read('olist_sellers_dataset.csv')
    assert orders.order_id.is_unique, 'Duplicate order keys'
    assert not items.duplicated(['order_id', 'order_item_id']).any(), 'Duplicate item keys'
    assert items.order_id.isin(orders.order_id).all(), 'Orphan item orders'
    # Stable tie breaker makes same-timestamp reviews reproducible.
    reviews = reviews.sort_values(['review_answer_timestamp', 'review_id', 'review_score'], na_position='first')
    latest = reviews.drop_duplicates('order_id', keep='last')
    orders = orders.merge(latest[['order_id', 'review_score']], on='order_id', how='left', validate='one_to_one')
    actual = pd.to_datetime(orders.order_delivered_customer_date)
    estimated = pd.to_datetime(orders.order_estimated_delivery_date)
    eligible = orders.order_status.eq('delivered') & actual.notna() & estimated.notna()
    orders['on_time'] = (actual <= estimated).astype('Int64').where(eligible)
    orders['date_key'] = pd.to_datetime(orders.order_purchase_timestamp).dt.strftime('%Y-%m-%d')
    orders = orders[['order_id', 'date_key', 'order_status', 'on_time', 'review_score']]
    products = products.merge(categories, on='product_category_name', how='left', validate='many_to_one')
    products['category'] = products.product_category_name_english.fillna(products.product_category_name).fillna('unknown')
    products = products[['product_id', 'category']]
    sellers = sellers[['seller_id', 'seller_state']]
    items = items[['order_id', 'order_item_id', 'seller_id', 'product_id', 'price', 'freight_value']]
    for frame, key in [(products, 'product_id'), (sellers, 'seller_id')]:
        assert frame[key].is_unique and frame[key].notna().all()
        assert items[key].isin(frame[key]).all(), f'Orphan {key}'
    dates = pd.DataFrame({'date_key': pd.date_range(orders.date_key.min(), orders.date_key.max())})
    dates['month'] = dates.date_key.dt.strftime('%Y-%m')
    dates['year'] = dates.date_key.dt.year
    dates['date_key'] = dates.date_key.dt.strftime('%Y-%m-%d')
    frames = dict(Orders=orders, Items=items, Products=products, Sellers=sellers, Dates=dates)
    for name, frame in frames.items():
        frame.to_csv(output / f'{name}.csv', index=False)
    delivered = orders[orders.on_time.notna()]
    summary = {'orders': len(orders), 'items': len(items), 'eligible_delivered': len(delivered),
               'late_orders': int(delivered.on_time.eq(0).sum()), 'on_time_rate': float(delivered.on_time.mean()),
               'item_value_brl': round(float(items.price.sum()), 2),
               'reviewed_orders': int(orders.review_score.notna().sum()),
               'average_review': float(orders.review_score.mean())}
    manifest = {'status': 'Locally recomputed from source CSVs', 'summary': summary,
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(data.glob('*.csv'))}}
    (output / 'validation.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(summary, indent=2))
    return frames, summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='data')
    parser.add_argument('--output', default='portfolio/powerbi/data')
    args = parser.parse_args()
    build(args.data, args.output)

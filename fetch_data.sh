#!/usr/bin/env bash
# Olist Brazilian E-Commerce Public Dataset (Kaggle: olistbr/brazilian-ecommerce, CC BY-NC-SA 4.0).
# Pinned GitHub mirror of the original CSVs; row counts are checked below.
set -euo pipefail
mkdir -p data
base=https://raw.githubusercontent.com/jorellano/E_commerce/ed9c8fb3bd5b8e365172bc613b2db2f755781717
for f in olist_orders_dataset olist_order_items_dataset olist_order_reviews_dataset olist_order_payments_dataset \
         olist_customers_dataset olist_sellers_dataset olist_products_dataset product_category_name_translation; do
  curl -fsSL "$base/$f.csv" -o "data/$f.csv"
done
python3 -c "import pandas as pd; n=len(pd.read_csv('data/olist_orders_dataset.csv')); assert n==99441, n; print('orders:', n)"

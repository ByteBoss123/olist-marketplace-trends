"""Independent pandas recompute of warehouse_results.json. Exits 1 on any mismatch."""
import json, pandas as pd
D = "data/"
o = pd.read_csv(D + "olist_orders_dataset.csv", parse_dates=["order_delivered_customer_date", "order_estimated_delivery_date"])
i = pd.read_csv(D + "olist_order_items_dataset.csv")
s = pd.read_csv(D + "olist_sellers_dataset.csv")
p = pd.read_csv(D + "olist_products_dataset.csv")
t = pd.read_csv(D + "product_category_name_translation.csv")
r = pd.read_csv(D + "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
res = json.load(open("warehouse_results.json")); bad = []
def chk(n, a, b, tol=1e-9):
    if abs(a - b) > tol * max(1, abs(a)): bad.append((n, a, b))
chk("fact_order rows", len(o), res["row_counts"]["fact_order"])
chk("fact_order_item rows", len(i), res["row_counts"]["fact_order_item"])
chk("dim_seller rows", s.seller_id.nunique(), res["row_counts"]["dim_seller"])
chk("orphan sellers", (~i.seller_id.isin(s.seller_id)).sum(), 0)
chk("orphan products", (~i.product_id.isin(p.product_id)).sum(), 0)
d = o[(o.order_status == "delivered") & o.order_delivered_customer_date.notna()]
chk("on_time_rate", (d.order_delivered_customer_date <= d.order_estimated_delivery_date).mean(), res["on_time_rate"])
p = p.merge(t, on="product_category_name", how="left")
p["category"] = p.product_category_name_english.fillna(p.product_category_name).fillna("unknown")
rv = r.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
x = i.merge(p[["product_id", "category"]], on="product_id").merge(rv, on="order_id", how="left")
rev = x.groupby("category").price.sum()
# avg_review in SQL is averaged over item rows (fact_order_item joined to fact_order)
avg_review = x.groupby("category").review_score.mean()
for c in res["categories_500plus_orders"]:
    chk(f"revenue {c['category']}", rev[c["category"]], c["item_revenue"], 1e-9)
    chk(f"review {c['category']}", avg_review[c["category"]], c["avg_review"], 1e-9)
print("mismatches:", bad or "none"); raise SystemExit(1 if bad else 0)

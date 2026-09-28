"""Independent pandas recompute of results.json (no shared code with the SQL). Exits 1 on any mismatch."""
import json, pandas as pd
o = pd.read_csv("data/olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"])
r = pd.read_csv("data/olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
d = o[(o.order_status == "delivered") & o.order_delivered_customer_date.notna()].copy()
d["late"] = (d.order_delivered_customer_date > d.order_estimated_delivery_date).astype(int)
d["mo"] = d.order_purchase_timestamp.dt.strftime("%Y-%m")
rv = r.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
res = json.load(open("results.json"))
bad = []
def chk(name, a, b, tol=1e-9):
    if abs(a - b) > tol: bad.append((name, a, b))
chk("delivered_orders", len(d), res["delivered_orders"], 0)
chk("overall_late_rate", d.late.mean(), res["overall_late_rate"])
for mo, g in d.groupby("mo"):
    chk(f"late_{mo}", g.late.mean(), res["monthly"][mo]["late_rate"])
j = d.merge(rv, on="order_id")
for k, g in j.groupby("late"):
    chk(f"avg_review_{k}", g.review_score.mean(), res["review_by_late"][str(k)]["avg_review"])
    chk(f"one_star_{k}", (g.review_score == 1).mean(), res["review_by_late"][str(k)]["one_star_share"])
print("mismatches:", bad or "none")
raise SystemExit(1 if bad else 0)

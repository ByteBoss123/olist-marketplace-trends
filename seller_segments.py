"""K-means seller segmentation on the warehouse's seller KPIs.

Run after build_warehouse.py. Writes results/seller_segments.json and results/seller_segments.csv.

Features per seller (sellers with at least MIN_ORDERS orders, so rates are not driven by one or two orders):
  log orders, log average item revenue per order, on-time delivery rate, average review score,
  freight as a share of item price. Standardized, then K-means for k = 2..8; k is chosen by silhouette score.
Stability: the chosen k is refit with 10 different seeds and compared to the reference fit with the adjusted Rand index.
"""
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

MIN_ORDERS = 10
K_RANGE = range(2, 9)
SEED = 42
FEATURES = ["log_orders", "log_avg_order_revenue", "on_time_rate", "avg_review", "freight_share"]


def seller_features(db="olist_warehouse.duckdb"):
    c = duckdb.connect(db, read_only=True)
    df = c.sql("""
        select f.seller_id,
               count(distinct f.order_id)                 as orders,
               sum(f.price)                               as item_revenue,
               sum(f.freight_value) / sum(f.price)        as freight_share,
               avg(o.delivered_on_time)                   as on_time_rate,
               avg(o.review_score)                        as avg_review
        from fact_order_item f join fact_order o using (order_id)
        group by 1
    """).df()
    c.close()
    n_all = len(df)
    df = df[(df.orders >= MIN_ORDERS) & df.on_time_rate.notna() & df.avg_review.notna()].copy()
    df["log_orders"] = np.log(df.orders)
    df["log_avg_order_revenue"] = np.log(df.item_revenue / df.orders)
    return df.reset_index(drop=True), n_all


def segment(df):
    X = StandardScaler().fit_transform(df[FEATURES])
    sil = {}
    for k in K_RANGE:
        labels = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit_predict(X)
        sil[k] = float(silhouette_score(X, labels))
    best_k = max(sil, key=sil.get)
    ref = KMeans(n_clusters=best_k, n_init=20, random_state=SEED).fit_predict(X)
    aris = [adjusted_rand_score(ref, KMeans(n_clusters=best_k, n_init=20, random_state=s).fit_predict(X))
            for s in range(10)]
    return sil, best_k, ref, aris


def main():
    df, n_all = seller_features()
    sil, best_k, labels, aris = segment(df)
    df["segment"] = labels
    prof = (df.groupby("segment")
              .agg(sellers=("seller_id", "size"), median_orders=("orders", "median"),
                   revenue=("item_revenue", "sum"), on_time_rate=("on_time_rate", "mean"),
                   avg_review=("avg_review", "mean"), freight_share=("freight_share", "median"))
              .reset_index())
    prof["revenue_share"] = prof.revenue / prof.revenue.sum()
    prof = prof.sort_values("revenue", ascending=False)
    out = dict(
        sellers_total=int(n_all), sellers_segmented=int(len(df)), min_orders=MIN_ORDERS, features=FEATURES,
        silhouette_by_k={str(k): round(v, 4) for k, v in sil.items()}, best_k=int(best_k),
        stability_ari_min=round(min(aris), 4), stability_ari_mean=round(float(np.mean(aris)), 4),
        segments=[{k: (round(v, 4) if isinstance(v, float) else int(v)) for k, v in r.items()}
                  for r in prof.to_dict(orient="records")],
    )
    Path("results").mkdir(exist_ok=True)
    json.dump(out, open("results/seller_segments.json", "w"), indent=2)
    df[["seller_id", "segment"] + FEATURES].to_csv("results/seller_segments.csv", index=False)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

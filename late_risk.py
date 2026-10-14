"""Late-delivery risk model and model-performance monitoring on real Olist orders.

Question: at the moment an order is approved, which orders are likely to arrive after the delivery date promised
to the customer, so operations can intervene (upgrade shipping, warn the customer) before the delay happens?

Leakage rules: only information known at approval time. Seller and route history come from orders *delivered
before this order was purchased*, so no future outcome leaks in. Split is chronological: train on orders
purchased before 2018-01-01, test on Jan-Aug 2018 (the months when late deliveries spiked).
Writes results/late_risk_metrics.json, results/monitoring_monthly.csv, results/dashboard.html.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

D, OUT = Path("data"), Path("results")
SPLIT = pd.Timestamp("2018-01-01")
END = pd.Timestamp("2018-09-01")
TOP = 0.10  # operations can act on the riskiest 10% of orders
SEED = 0


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def load():
    r = lambda n: pd.read_csv(D / f"olist_{n}_dataset.csv")
    o = r("orders")
    for c in ["order_purchase_timestamp", "order_approved_at", "order_delivered_customer_date",
              "order_estimated_delivery_date"]:
        o[c] = pd.to_datetime(o[c])
    o = o[(o.order_status == "delivered") & o.order_delivered_customer_date.notna() & o.order_approved_at.notna()]
    o["late"] = (o.order_delivered_customer_date.dt.normalize() > o.order_estimated_delivery_date).astype(int)
    items, prod, sel, cus, geo = r("order_items"), r("products"), r("sellers"), r("customers"), r("geolocation")
    zipc = geo.groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].median()
    items = items.merge(prod[["product_id", "product_weight_g", "product_length_cm", "product_height_cm",
                              "product_width_cm", "product_category_name"]], on="product_id", how="left")
    items["vol_cm3"] = items.product_length_cm * items.product_height_cm * items.product_width_cm
    items = items.merge(sel, on="seller_id", how="left")
    agg = items.groupby("order_id").agg(n_items=("order_item_id", "count"), n_sellers=("seller_id", "nunique"),
                                        price=("price", "sum"), freight=("freight_value", "sum"),
                                        weight_g=("product_weight_g", "sum"), vol_cm3=("vol_cm3", "sum"),
                                        seller_id=("seller_id", "first"), seller_zip=("seller_zip_code_prefix", "first"),
                                        seller_state=("seller_state", "first"),
                                        category=("product_category_name", "first"))
    df = o.merge(agg, on="order_id").merge(cus[["customer_id", "customer_zip_code_prefix", "customer_state"]],
                                           on="customer_id")
    s = zipc.reindex(df.seller_zip).to_numpy()
    c = zipc.reindex(df.customer_zip_code_prefix).to_numpy()
    df["distance_km"] = haversine(s[:, 0], s[:, 1], c[:, 0], c[:, 1])
    df["same_state"] = (df.seller_state == df.customer_state).astype(int)
    df["promised_days"] = (df.order_estimated_delivery_date - df.order_purchase_timestamp).dt.total_seconds() / 86400
    df["approve_hours"] = (df.order_approved_at - df.order_purchase_timestamp).dt.total_seconds() / 3600
    df["purchase_dow"] = df.order_purchase_timestamp.dt.dayofweek
    df["purchase_month"] = df.order_purchase_timestamp.dt.month
    df["freight_ratio"] = df.freight / df.price.clip(lower=1)
    return df.sort_values("order_purchase_timestamp").reset_index(drop=True)


def prior_late_rate(df, key, prior=50):
    """Late rate of earlier orders for the same key, counting only orders already DELIVERED before this order's
    purchase time. Smoothed toward the global rate with `prior` pseudo-orders."""
    ev = df[[key, "order_delivered_customer_date", "late"]].rename(columns={"order_delivered_customer_date": "t"})
    ev = ev.sort_values("t")
    ev["cum_n"] = ev.groupby(key).cumcount() + 1
    ev["cum_late"] = ev.groupby(key)["late"].cumsum()
    q = df[[key, "order_purchase_timestamp"]].reset_index().sort_values("order_purchase_timestamp")
    m = pd.merge_asof(q, ev[[key, "t", "cum_n", "cum_late"]], left_on="order_purchase_timestamp", right_on="t",
                      by=key, direction="backward", allow_exact_matches=False)
    m = m.set_index("index").sort_index()
    n, late = m.cum_n.fillna(0), m.cum_late.fillna(0)
    # The smoothing prior must also be available at the query time. A global
    # training-period mean leaks future outcomes into early training rows.
    global_events = ev[["t", "late"]].copy()
    global_events["global_n"] = np.arange(1, len(global_events) + 1)
    global_events["global_late"] = global_events.late.cumsum()
    history = pd.merge_asof(q, global_events[["t", "global_n", "global_late"]],
                            left_on="order_purchase_timestamp", right_on="t",
                            direction="backward", allow_exact_matches=False)
    history = history.set_index("index").sort_index()
    # Fixed neutral prior before any outcomes exist, never learned from future data.
    g = (history.global_late / history.global_n).fillna(0.5)
    return (late + prior * g) / (n + prior), n


FEATURES = ["distance_km", "same_state", "promised_days", "approve_hours", "purchase_dow", "purchase_month",
            "n_items", "n_sellers", "price", "freight", "freight_ratio", "weight_g", "vol_cm3",
            "seller_prior_late", "seller_prior_orders", "route_prior_late"]


# Calendar and running-history features shift by construction, so drift is watched on shipment features only.
DRIFT_FEATURES = ["distance_km", "promised_days", "approve_hours", "n_items", "price", "freight", "weight_g", "vol_cm3"]


def at_top(y, p, frac=TOP):
    k = max(1, int(len(p) * frac))
    idx = np.argsort(-p)[:k]
    return {"precision": round(float(y[idx].mean()), 3), "late_caught": int(y[idx].sum()),
            "late_total": int(y.sum()), "recall": round(float(y[idx].sum() / max(1, y.sum())), 3), "flagged": k}


def score(y, p):
    return {"pr_auc": round(float(average_precision_score(y, p)), 3), "roc_auc": round(float(roc_auc_score(y, p)), 3),
            "brier": round(float(brier_score_loss(y, p)), 4), "top10pct": at_top(y, p)}


def psi(ref, cur, bins=10, eps=1e-4):
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref) + eps
    c = np.histogram(cur, edges)[0] / len(cur) + eps
    return float(np.sum((c - r) * np.log(c / r)))


def main():
    df = load()
    df["seller_prior_late"], df["seller_prior_orders"] = prior_late_rate(df, "seller_id")
    df["route"] = df.seller_state + ">" + df.customer_state
    df["route_prior_late"], _ = prior_late_rate(df, "route")
    df = df[df.order_purchase_timestamp < END]
    tr = df[(df.order_purchase_timestamp < SPLIT) & (df.order_delivered_customer_date < SPLIT)]
    te = df[df.order_purchase_timestamp >= SPLIT]
    Xtr, Xte = tr[FEATURES].fillna(tr[FEATURES].median()), te[FEATURES].fillna(tr[FEATURES].median())
    ytr, yte = tr.late.to_numpy(), te.late.to_numpy()

    models = {
        "seller_history_only": None,
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "gradient_boosting": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                                            l2_regularization=1.0, random_state=SEED),
    }
    preds, res = {}, {}
    for name, m in models.items():
        if m is None:
            preds[name] = te.seller_prior_late.to_numpy()
        else:
            m.fit(Xtr, ytr)
            preds[name] = m.predict_proba(Xte)[:, 1]
        res[name] = score(yte, preds[name])
    gb = models["gradient_boosting"]

    # permutation importance on test PR-AUC (which signals matter)
    rng = np.random.default_rng(SEED)
    base = average_precision_score(yte, preds["gradient_boosting"])
    imp = {}
    for f in FEATURES:
        Xp = Xte.copy()
        Xp[f] = rng.permutation(Xp[f].to_numpy())
        imp[f] = round(base - average_precision_score(yte, gb.predict_proba(Xp)[:, 1]), 4)
    top_imp = dict(sorted(imp.items(), key=lambda t: -t[1])[:6])

    # monthly monitoring: volume, actual vs predicted late rate, PR-AUC, top-10% recall, feature drift (PSI)
    te = te.assign(p=preds["gradient_boosting"], month=te.order_purchase_timestamp.dt.to_period("M").astype(str))
    rows = []
    for mo, g in te.groupby("month"):
        drift = {f: psi(Xtr[f].to_numpy(), g[f].fillna(tr[f].median()).to_numpy()) for f in DRIFT_FEATURES}
        worst = max(drift, key=drift.get)
        rows.append({"month": mo, "orders": len(g), "actual_late_rate": round(g.late.mean(), 4),
                     "predicted_late_rate": round(g.p.mean(), 4),
                     "pr_auc": round(average_precision_score(g.late, g.p), 3) if g.late.nunique() > 1 else None,
                     "top10_recall": at_top(g.late.to_numpy(), g.p.to_numpy())["recall"],
                     "calibration_gap": round(g.late.mean() - g.p.mean(), 4),
                     "max_feature_psi": round(drift[worst], 3), "most_drifted_feature": worst})
    mon = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    mon.to_csv(OUT / "monitoring_monthly.csv", index=False)
    te[["order_id", "month", "seller_id", "customer_state", "seller_state", "distance_km", "promised_days", "late",
        "p"]].rename(columns={"p": "late_risk"}).to_csv(OUT / "test_order_scores.csv", index=False)

    out = {"orders_modeled": len(df), "train_orders": len(tr), "test_orders": len(te),
           "train_late_rate": round(float(ytr.mean()), 4), "test_late_rate": round(float(yte.mean()), 4),
           "split": "train: purchased and delivered before 2018-01-01; test: Jan-Aug 2018", "features": FEATURES,
           "test": res, "permutation_importance_pr_auc_drop": top_imp, "monitoring": rows}
    (OUT / "late_risk_metrics.json").write_text(json.dumps(out, indent=2))
    dashboard(mon, res, top_imp)
    print(json.dumps({k: out[k] for k in ("train_orders", "test_orders", "train_late_rate", "test_late_rate", "test",
                                          "permutation_importance_pr_auc_drop")}, indent=2))
    print(mon.to_string(index=False))


def dashboard(mon, res, imp):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=("Late-delivery rate: actual vs model forecast",
                                        "Model quality by month (PR-AUC, share of late orders caught in top 10% risk)",
                                        "Shipment-feature drift vs training data (max PSI; >0.25 = major)"))
    fig.add_scatter(x=mon.month, y=mon.actual_late_rate, name="Actual late rate", row=1, col=1)
    fig.add_scatter(x=mon.month, y=mon.predicted_late_rate, name="Predicted late rate", row=1, col=1,
                    line=dict(dash="dash"))
    fig.add_scatter(x=mon.month, y=mon.pr_auc, name="PR-AUC", row=2, col=1)
    fig.add_scatter(x=mon.month, y=mon.top10_recall, name="Late orders caught (top 10%)", row=2, col=1)
    fig.add_bar(x=mon.month, y=mon.max_feature_psi, name="Max feature PSI", text=mon.most_drifted_feature, row=3, col=1)
    fig.add_hline(y=0.25, line_dash="dot", row=3, col=1)
    gb = res["gradient_boosting"]
    fig.update_layout(height=900, template="plotly_white",
                      title=f"Late-delivery risk monitoring, Jan-Aug 2018 (test PR-AUC {gb['pr_auc']}, "
                            f"top-10% catches {gb['top10pct']['recall']:.0%} of late orders)")
    fig.write_html(OUT / "dashboard.html", include_plotlyjs="cdn")


if __name__ == "__main__":
    main()

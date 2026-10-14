import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import late_risk as L  # noqa: E402


@pytest.fixture(scope="module")
def df():
    import os
    os.chdir(ROOT)
    d = L.load()
    d["seller_prior_late"], d["seller_prior_orders"] = L.prior_late_rate(d, "seller_id")
    return d


def test_seller_history_uses_only_orders_delivered_before_purchase(df):
    sample = df.sample(300, random_state=0)
    for _, r in sample.iterrows():
        global_past = df[df.order_delivered_customer_date < r.order_purchase_timestamp]
        g = global_past.late.mean() if len(global_past) else 0.5
        past = df[(df.seller_id == r.seller_id) & (df.order_delivered_customer_date < r.order_purchase_timestamp)]
        expect = (past.late.sum() + 50 * g) / (len(past) + 50)
        assert r.seller_prior_orders == len(past)
        assert abs(r.seller_prior_late - expect) < 1e-9


def test_future_outcomes_cannot_change_past_features(df):
    cutoff = pd.Timestamp("2017-06-01")
    altered = df.copy()
    future = altered.order_delivered_customer_date >= cutoff
    altered.loc[future, "late"] = 1 - altered.loc[future, "late"]
    changed, _ = L.prior_late_rate(altered, "seller_id")
    past = df.order_purchase_timestamp < cutoff
    assert np.allclose(changed[past], df.loc[past, "seller_prior_late"])


def test_delivered_orders_and_late_definition(df):
    assert len(df) == 96456  # delivered, approved, with a delivery date and at least one item
    late = df.order_delivered_customer_date.dt.normalize() > df.order_estimated_delivery_date
    assert (df.late == late.astype(int)).all()


def test_published_metrics():
    m = json.loads((ROOT / "results" / "late_risk_metrics.json").read_text())
    t = m["test"]
    assert t["gradient_boosting"]["pr_auc"] > t["logistic_regression"]["pr_auc"] > t["seller_history_only"]["pr_auc"]
    top = t["gradient_boosting"]["top10pct"]
    assert top["precision"] > 2 * m["test_late_rate"]          # top-10% risk list is >2x the base rate
    mon = {r["month"]: r for r in m["monitoring"]}
    # the Feb-Mar 2018 surge: input drift stayed under the 0.25 alarm, the calibration gap did not
    for mo in ("2018-02", "2018-03"):
        row = mon[mo]
        assert row["max_feature_psi"] < 0.25
        assert row["actual_late_rate"] > row["predicted_late_rate"]
        assert row["calibration_gap"] == pytest.approx(
            row["actual_late_rate"] - row["predicted_late_rate"], abs=0.00011)

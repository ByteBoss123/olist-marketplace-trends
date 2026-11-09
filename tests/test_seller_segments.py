import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import seller_segments as S  # noqa: E402


def setup_module(_):
    os.chdir(ROOT)


def test_only_sellers_with_enough_orders_and_valid_rates():
    df, n_all = S.seller_features()
    assert n_all == 3095
    assert (df.orders >= S.MIN_ORDERS).all()
    assert df[S.FEATURES].notna().all().all()
    assert df.on_time_rate.between(0, 1).all() and df.avg_review.between(1, 5).all()


def test_segmentation_is_reproducible_and_stable():
    df, _ = S.seller_features()
    sil, k, a, aris = S.segment(df)
    _, k2, b, _ = S.segment(df)
    assert k == k2 and (a == b).all()
    assert min(aris) > 0.9
    assert k == max(sil, key=sil.get)

# Olist Seller Performance & Fulfillment KPI Warehouse

**Stack:** SQL (Amazon Redshift, DuckDB), Python (pandas)

## Business Problem
A marketplace lives on seller reliability. When deliveries slip, customers leave bad reviews, and bad
reviews push buyers away from every seller on the platform. Operations and category managers need
**one trusted place to track seller, category and monthly performance**, and they need to know
**when delivery breaks down and what it costs in customer satisfaction**, so they can plan carrier
capacity and manage sellers before peak periods.

## Steps Taken to Resolve
1. **Sourced real marketplace data:** the Olist Brazilian e-commerce dataset, 99,441 orders and 112,650 order items (Sep 2016 to Oct 2018) from 3,095 sellers, with delivery timestamps, payments and reviews.
2. **Modeled a star schema:** four dimensions (customer, seller, product with English category, date) and two facts (order, order item), documented in `sql/warehouse.sql`.
3. **Enforced data integrity:** 13 automated tests for primary-key uniqueness, foreign-key orphans and row loss versus source (`sql/integrity_tests.sql`); the build fails on any violation.
4. **Exposed self-service KPIs:** seller, category and monthly KPI views (orders, revenue, on-time rate, average review).
5. **Analyzed the trend and the driver:** late-delivery rate by purchase month, and review scores for late versus on-time orders.
6. **Verified independently:** recomputed row counts, orphan checks, the on-time rate, category revenue and reviews, and every monthly rate in pandas with no shared code.

## Achievements
- Built a warehouse of **99,441 orders and 112,650 order items from 3,095 sellers** with **0 duplicate keys, 0 orphaned keys and 0 rows lost** (13 of 13 integrity tests pass).
- Showed late deliveries averaged **8.1%** but spiked to **14.3%** in the peak-volume month (Nov 2017, 7,288 orders) and **21.4%** in Mar 2018.
- Linked late delivery to satisfaction: late orders average a **2.54** review vs **4.28** on time, with **6.9x** more 1-star reviews (46.7% vs 6.8%).
- Category view across 74 product categories: health & beauty leads item revenue ($1.26M); office furniture has the lowest average review among the 27 major categories (500+ orders): 3.48 vs a 4.02 marketplace average.
- Independent pandas checks: **0 mismatches** on the warehouse and the trend analysis.

## Amazon Redshift deployment (verified 2026-09-28)
The same Olist star schema runs in **Amazon Redshift Serverless** (us-east-1, schema `vendorpulse`, tables created
2026-08-11 by the Vendor-Pulse project). Verified today through the Redshift Data API:

| Table | Rows |
|---|---|
| dim_customer | 99,441 |
| dim_seller | 3,095 |
| dim_product | 32,951 |
| dim_date | 774 |
| fact_orders | 99,441 |
| fact_order_items | 112,650 |
| fact_payments | 99,440 |
| fact_reviews | 98,673 |
| seller_kpis | 3,095 |

`redshift/integrity_checks_redshift.sql` (11 primary-key and foreign-key checks) returns **0 violations** in Redshift.
Order-item on-time rate in Redshift: 101,481 of 112,650 items = **90.09%** (items on non-delivered orders count as
not on time). The DuckDB build here reports the delivered-order rate instead (91.9%); both are correct for their definition.

## Definitions
- **Delivered order:** `order_status = 'delivered'` with a customer delivery timestamp (96,470 orders).
- **Late:** delivered to the customer after `order_estimated_delivery_date`.
- **Review:** one per order, the latest answer (duplicate reviews per order are removed).

## Results (`results.json`)
| Finding | Value |
|---|---|
| Overall late-delivery rate | 8.1% (7,826 of 96,470) |
| Peak-volume month, Nov 2017 (7,288 orders) | 14.3% late |
| Feb 2018 / Mar 2018 | 16.0% / 21.4% late |
| Average review, on-time vs late | 4.28 vs 2.54 |
| 1-star share, on-time vs late | 6.8% vs 46.7% (6.9x) |

Late delivery is associated with lower review scores. This is observational data, so it is a driver
of review scores in the descriptive sense, not a causal estimate.

## Verification
| Check | Result |
|---|---|
| `python build_warehouse.py` | builds the star schema, runs 13 integrity tests (0 violations), writes `warehouse_results.json` |
| `python run.py` (DuckDB SQL in `sql/marketplace_trends.sql`) | builds the trend tables, writes `results.json` |
| `python validation/validate_warehouse.py` | 0 mismatches on row counts, orphans, on-time rate, category revenue and reviews |
| `python validation/validate.py` (pandas, no shared code with the SQL) | 0 mismatches across every monthly rate and review statistic |

## Run
```bash
pip install duckdb pandas
./fetch_data.sh
python build_warehouse.py
python run.py
python validation/validate_warehouse.py
python validation/validate.py
```

## Late-delivery risk model and model monitoring (`late_risk.py`)

**Question.** When an order is approved, which orders will miss the delivery date promised to the customer, so
operations can act (faster shipping, proactive customer message) before the delay happens?

**Data and rules.** 96,456 delivered orders. Features known at approval time only: seller-to-customer distance
(zip-code centroids from the 1,000,163-row Olist geolocation file), same-state flag, promised delivery window,
approval delay, items, sellers, price, freight, weight, volume, purchase month and weekday, and seller and
route late-rate history counted **only from orders delivered before this order was purchased** (a test checks
this against a brute-force recount). Chronological split: train on 43,679 orders purchased before 2018 (5.6% late),
test on 52,777 orders from Jan-Aug 2018 (7.7% late).

| Model (test, Jan-Aug 2018) | PR-AUC | ROC-AUC | Top 10% riskiest orders: late share | Late orders caught |
|---|---|---|---|---|
| Seller late-rate history only | 0.078 | 0.51 | 7.0% | 367 of 4,078 (9%) |
| Logistic regression | 0.098 | 0.60 | 9.6% | 509 (12.5%) |
| **Gradient boosting** | **0.132** | **0.66** | **15.6% (2.0x the 7.7% base rate)** | **825 (20%)** |

Strongest signals (permutation importance): distance, promised delivery window, purchase month, route history.
The model is a ranking aid, not a precise forecaster: most late deliveries are not predictable from order data.

**Caveat.** The data ends in October 2018, so only orders already delivered by then are included. The last test months (July-August 2018) therefore over-represent fast deliveries; read their rates and drift with that in mind.

**Monitoring** (`results/monitoring_monthly.csv`, `results/dashboard.html`). Each month: actual vs predicted late
rate (calibration gap), PR-AUC, share of late orders caught, and input drift (PSI) on shipment features.

| Month | Actual late | Predicted | Gap | Max shipment-feature PSI |
|---|---|---|---|---|
| 2018-01 | 5.7% | 4.8% | +0.9 pts | 0.09 |
| **2018-02** | **14.1%** | 5.2% | **+8.9 pts** | 0.18 |
| **2018-03** | **19.0%** | 6.3% | **+12.7 pts** | 0.20 |
| 2018-06 | 1.2% | 4.4% | -3.3 pts | 0.68 (approval delay) |
| 2018-08 | 6.2% | 6.9% | -0.7 pts | 1.51 (promised window) |

**Finding.** The Feb-Mar 2018 delivery surge did **not** trip the input-drift alarm (PSI stayed under 0.25): the
orders looked normal, the delivery network did not. Only the calibration gap (outcomes vs forecast) caught it.
Later months show the opposite: large input drift while late rates fell (the median promised window swung from 27 days for June orders to 13 days for August orders).
So monitoring needs both signals; input drift alone would have missed the one month operations most needed.

```bash
bash fetch_data.sh
python late_risk.py && pytest -q tests
```

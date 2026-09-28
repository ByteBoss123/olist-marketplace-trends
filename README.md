# Olist Seller Performance & Fulfillment KPI Warehouse

**Stack:** SQL (DuckDB), Python (pandas)

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

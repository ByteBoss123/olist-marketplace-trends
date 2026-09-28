# Olist Marketplace Delivery Trends & Review Drivers

**Stack:** SQL (DuckDB), Python (pandas)

## Business Problem
A marketplace lives on seller reliability. When deliveries slip, customers leave bad reviews, and bad
reviews push buyers away from every seller on the platform. Operations needs to know **when delivery
performance breaks down** and **how much it costs in customer satisfaction**, so it can plan carrier
capacity and set seller expectations before peak periods.

## Steps Taken to Resolve
1. **Sourced real marketplace data:** 99,441 Olist orders (Sep 2016 to Oct 2018) from 3,095 sellers, with purchase, delivery and estimated-delivery timestamps plus customer reviews.
2. **Defined auditable metrics:** delivered order, late delivery (after the estimated date), and one review per order (latest answer, duplicates removed).
3. **Modeled the data in SQL:** a delivered-orders fact table, a de-duplicated review dimension, a monthly late-rate table, and a review-by-delivery-status table.
4. **Analyzed the trend and the driver:** tracked late-delivery rate by purchase month and compared review scores for late versus on-time orders.
5. **Verified independently:** recomputed every monthly rate and review statistic in pandas with no shared code.

## Achievements
- Showed late deliveries averaged **8.1%** but spiked to **14.3%** in the peak-volume month (Nov 2017, 7,288 orders) and **21.4%** in Mar 2018.
- Linked late delivery to customer satisfaction: late orders average a **2.54** review score vs **4.28** on time, with **6.9x** more 1-star reviews (46.7% vs 6.8%).
- Independent pandas check: **0 mismatches** across every monthly rate and review statistic.

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
| `python run.py` (DuckDB SQL in `sql/marketplace_trends.sql`) | builds 4 tables, writes `results.json` |
| `python validation/validate.py` (pandas, no shared code with the SQL) | 0 mismatches across every monthly rate and review statistic |

## Run
```bash
pip install duckdb pandas
./fetch_data.sh
python run.py
python validation/validate.py
```

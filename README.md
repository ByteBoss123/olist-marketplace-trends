# Olist Marketplace Delivery Trends & Review Drivers

Extends the Seller Performance & Fulfillment KPI Warehouse with a monthly trend and a driver analysis on
the real Olist Brazilian e-commerce dataset (99,441 orders, Sep 2016 to Oct 2018).

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

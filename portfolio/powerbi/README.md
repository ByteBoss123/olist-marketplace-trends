# Olist Power BI report draft

This is a locally validated data export and a Power BI implementation pack, **not a finished PBIX or PBIP report**. Power BI Desktop is not available in the authoring environment. DAX and Power Query below require Desktop validation.

## Build and import

1. From the repository root run `python portfolio/export_report.py`.
2. In Power BI Desktop create a blank query called `DataFolder`, with a text value pointing to the absolute `portfolio/powerbi/data` folder. Use a trailing path separator.
3. Create each query from its `.pq` file, using the exact table name in the filename. Apply changes.
4. Create the relationships below, all active, one-to-many, **single direction**. Disable automatic date/time. Mark `Dates` as a date table using `date_key`.
5. Add the measures in `measures.dax` individually to `Orders`. Format ratios as percentages, review scores as 0.00, monetary values as BRL (R$), counts as whole numbers.
6. Build the three pages below and save as `Olist.pbip`. Verify the acceptance checks before describing this as a built Power BI report.

| One side | Many side |
| --- | --- |
| Dates[date_key] | Orders[date_key] |
| Orders[order_id] | Items[order_id] |
| Sellers[seller_id] | Items[seller_id] |
| Products[product_id] | Items[product_id] |

Seller and category filters reach Items. The scoped order measures explicitly transfer the distinct order IDs back to Orders. Do not turn on bidirectional relationships. An order spanning categories or sellers appears once in each selected group, so order counts are not additive across those groups. Item value is additive. Orders with no items remain in the unfiltered order totals.

## Report pages

Use a 16:9 canvas, a white background, navy headings and teal data marks. Use orange only to highlight late deliveries. Display a permanent subtitle: Historical Olist mirror, 2016–2018. No live refresh.

| Page | Visuals and interaction |
| --- | --- |
| Executive overview | Cards: scoped orders, eligible delivered orders, on-time rate, item value BRL. Line: month vs late rate. Bar: category vs item value. Month and seller-state slicers. A text note defines value as item prices excluding freight, not profit or platform revenue. |
| Delivery and reviews | Month vs late rate and delivered-order count as separate charts. Bar: delivery status vs average review (use on_time as category with 1 = on time and 0 = late, exclude blanks). Cards: late orders and reviewed eligible orders. Month/category slicers. State that association is not causation. |
| Seller and category explorer | Matrix: seller ID, state, scoped orders, eligible delivered orders, on-time rate, average review and item value. Category/month/state slicers. Default visual filter: eligible delivered orders >= 50 (portfolio design choice, not a business-approved rule). Show denominator beside each rate. |

## Metric contracts

- Order: one source order ID, including canceled/unavailable orders in total orders.
- Delivery denominator: delivered status with actual and estimated timestamps present.
- On time: actual timestamp <= estimated timestamp, preserving the repository definition. Date-only comparisons would be a different definition.
- Review: latest answer per order, with review ID then score as deterministic tie breakers. Review averages exclude blank scores. Category/seller review scores count each matching order once.
- Item value: sum of item price in Brazilian reais, across all source item rows regardless of order status. This is not recognized revenue, net revenue, or realized profit. No FX conversion.
- Refresh: static public historical dataset. Owner: portfolio author. No RLS needed for this public dataset; this is not an enterprise security design.
- Source: pinned mirror in `fetch_data.sh`; checksums and source counts are in `data/validation.json`. This mirror contains 100,000 review rows, covering 99,441 order IDs. Do not silently equate its review coverage with other versions of Olist.

## Acceptance checks in Desktop

- With no filters, compare every headline to `data/validation.json`: 99,441 orders, 112,650 items, 96,470 eligible deliveries, 7,826 late orders, 91.887633% on time, R$13,591,643.70 item value.
- November 2017: 7,288 eligible deliveries and 14.311196% late. March 2018: 7,003 eligible deliveries and 21.362273% late.
- Select a seller and category together. Independently filter Items to both values, take distinct order IDs, and calculate the order-level average. Match the visual, including totals.
- Multi-item orders must count once in order measures, and all item prices must contribute to item value.
- Empty selections should return blank rates, not 100% on time. Missing delivery timestamps never count as on-time deliveries.
- Test slicers on every page, save/reopen the PBIP, and capture screenshots only after confirming rendering and filters.

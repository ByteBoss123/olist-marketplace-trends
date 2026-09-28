"""Build the star-schema warehouse, run the integrity tests, and write warehouse_results.json. Exits 1 on any violation."""
import duckdb, json
c = duckdb.connect("olist_warehouse.duckdb")
c.execute(open("sql/warehouse.sql").read())
tests = c.sql(open("sql/integrity_tests.sql").read()).fetchall()
rows = {t: c.sql(f"select count(*) from {t}").fetchone()[0]
        for t in ["dim_customer", "dim_seller", "dim_product", "dim_date", "fact_order", "fact_order_item"]}
cat = c.sql("""select category, orders, item_revenue, avg_review from kpi_category
               where orders >= 500 order by item_revenue desc""").fetchall()
out = dict(row_counts=rows, integrity_tests={t: v for t, v in tests},
           total_violations=sum(v for _, v in tests),
           on_time_rate=c.sql("select avg(delivered_on_time) from fact_order").fetchone()[0],
           categories_500plus_orders=[dict(category=a, orders=b, item_revenue=r, avg_review=v) for a, b, r, v in cat])
json.dump(out, open("warehouse_results.json", "w"), indent=2, default=float)
print(json.dumps({k: out[k] for k in ["row_counts", "total_violations", "on_time_rate"]}, indent=2, default=float))
raise SystemExit(1 if out["total_violations"] else 0)

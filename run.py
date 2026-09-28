"""Build the DuckDB tables and print the headline results as JSON."""
import duckdb, json
c = duckdb.connect("olist_trends.duckdb")
c.execute(open("sql/marketplace_trends.sql").read())
m = c.sql("select strftime(purchase_month,'%Y-%m') mo, delivered_orders, late_rate from agg_monthly_late_rate").fetchall()
r = {int(k): dict(orders=n, avg_review=a, one_star_share=s) for k, n, a, s in c.sql("select * from agg_review_by_delivery").fetchall()}
tot = c.sql("select count(*), avg(is_late) from fct_delivered_orders").fetchone()
out = dict(delivered_orders=tot[0], overall_late_rate=tot[1],
           monthly={mo: dict(orders=n, late_rate=lr) for mo, n, lr in m}, review_by_late=r)
json.dump(out, open("results.json", "w"), indent=2, default=float)
print(json.dumps(out, indent=2, default=float))

"""Sort-key benchmark: does ordering the order-item fact table by purchase date speed up date-range queries?

Redshift skips 1 MB blocks whose min/max date range misses the filter (zone maps), which is why
fact tables get SORTKEY(date). DuckDB keeps the same min/max statistics per row group. This script
loads fact_order_item twice into one DuckDB file, in arrival order (by order_id, effectively random
in time) and sorted by date_key, and times the same month-range KPI queries on both.

Row groups are set to 2,048 rows (56 groups for 112,650 rows) so pruning can happen at this data
size; DuckDB's default 122,880-row groups would put the whole table in one group.

Design fixed before running: the 20 full calendar months 2017-01..2018-08, each query run
5 warm-up + 50 timed times per table, alternating tables; report median per table and the median
of per-month speedups. Results: benchmark/sort_key_results.json.
"""
import json, os, statistics, time
import duckdb

DB = "benchmark/bench.duckdb"
if os.path.exists(DB):
    os.remove(DB)
con = duckdb.connect()
con.execute("attach 'olist_warehouse.duckdb' as w (read_only)")
con.execute(f"attach '{DB}' as b (row_group_size 2048)")
con.execute("create table b.unsorted as select * from w.fact_order_item order by order_id")
con.execute("create table b.sorted   as select * from w.fact_order_item order by date_key, order_id")
con.execute("checkpoint b")

n = con.execute("select count(*) from b.unsorted").fetchall()[0][0]
assert n == con.execute("select count(*) from b.sorted").fetchall()[0][0] == con.execute("select count(*) from w.fact_order_item").fetchall()[0][0]
months = [r[0] for r in con.execute("""select distinct date_trunc('month', date_key)::date m from b.sorted
                                       where m between '2017-01-01' and '2018-08-01' order by m""").fetchall()]

def rowgroups_scanned(table, lo, hi):
    """Row groups whose date_key min/max overlaps [lo, hi): what min/max skipping can't avoid."""
    q = f"""select count(*) from (
              select row_group_id, min(stats['min']) mn, max(stats['max']) mx
              from pragma_storage_info('b.{table}') where column_name = 'date_key' and segment_type = 'DATE' group by 1)
            where cast(mx as date) >= DATE '{lo}' and cast(mn as date) < DATE '{hi}'"""
    return con.execute(q).fetchall()[0][0]

QUERY = """select count(distinct order_id), sum(price), sum(freight_value)
           from b.{t} where date_key >= DATE '{lo}' and date_key < DATE '{lo}' + interval 1 month"""
total_groups = {t: con.execute(f"select count(distinct row_group_id) from pragma_storage_info('b.{t}')").fetchall()[0][0]
                for t in ["unsorted", "sorted"]}
per_month = []
for lo in months:
    hi = con.execute(f"select (DATE '{lo}' + interval 1 month)::date").fetchall()[0][0]
    a = con.execute(QUERY.format(t="unsorted", lo=lo)).fetchall()
    b = con.execute(QUERY.format(t="sorted", lo=lo)).fetchall()
    assert a[0][0] == b[0][0] and all(abs(x - y) < 1e-6 for x, y in zip(a[0][1:], b[0][1:])), (lo, a, b)  # same answer
    times = {"unsorted": [], "sorted": []}
    for i in range(55):
        for t in ("unsorted", "sorted"):
            s = time.perf_counter(); con.execute(QUERY.format(t=t, lo=lo)).fetchall()
            if i >= 5:
                times[t].append((time.perf_counter() - s) * 1000)
    mu, ms = statistics.median(times["unsorted"]), statistics.median(times["sorted"])
    per_month.append(dict(month=str(lo), rows=a[0][0], median_ms_unsorted=round(mu, 3), median_ms_sorted=round(ms, 3),
                          speedup_pct=round(100 * (1 - ms / mu), 1),
                          rowgroups_overlapping_unsorted=rowgroups_scanned("unsorted", lo, hi),
                          rowgroups_overlapping_sorted=rowgroups_scanned("sorted", lo, hi)))

all_u = statistics.median(m["median_ms_unsorted"] for m in per_month)
all_s = statistics.median(m["median_ms_sorted"] for m in per_month)
out = dict(rows=n, row_group_size=2048, row_groups=total_groups, months=len(per_month), runs_per_query=50,
           duckdb=duckdb.__version__,
           median_query_ms=dict(unsorted=round(all_u, 3), sorted=round(all_s, 3)),
           median_latency_reduction_pct=round(100 * (1 - all_s / all_u), 1),
           median_of_monthly_speedups_pct=round(statistics.median(m["speedup_pct"] for m in per_month), 1),
           months_faster_sorted=sum(m["speedup_pct"] > 0 for m in per_month),
           median_rowgroups_overlapping=dict(unsorted=statistics.median(m["rowgroups_overlapping_unsorted"] for m in per_month),
                                             sorted=statistics.median(m["rowgroups_overlapping_sorted"] for m in per_month)),
           per_month=per_month)
json.dump(out, open("benchmark/sort_key_results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "per_month"}, indent=1))
con.close(); os.remove(DB)

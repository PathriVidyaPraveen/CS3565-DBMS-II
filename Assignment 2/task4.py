import psycopg2
import json
import os
from datetime import datetime, timedelta

PLAN_DIR = "../Task2/plans"

conn = psycopg2.connect(
    dbname="tpch_db",
    user="postgres",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# query definitions

def query1(d):
    return f"""
    SELECT
    SUM(l_quantity),
    SUM(l_extendedprice),
    SUM(l_extendedprice*(1-l_discount)),
    SUM(l_extendedprice*(1-l_discount)*(1+l_tax)),
    AVG(l_quantity),
    AVG(l_extendedprice),
    AVG(l_discount),
    COUNT(*)
    FROM lineitem
    WHERE l_shipdate <= DATE '{d}'
    """

def query2(d):
    return f"""
    SELECT
    o_orderpriority,
    count(*) AS order_count
    FROM orders o
    WHERE
    o_orderdate >= DATE '1992-01-01'
    AND o_orderdate < DATE '{d}'
    AND EXISTS (
        SELECT 1
        FROM lineitem l
        WHERE l.l_orderkey=o.o_orderkey
        AND l.l_commitdate<l.l_receiptdate
    )
    GROUP BY o_orderpriority
    """

def query3(d):
    return f"""
    SELECT
    l.l_orderkey,
    l.l_extendedprice*(1-l.l_discount) AS revenue,
    o.o_orderdate,
    o.o_shippriority
    FROM customer c
    JOIN orders o ON c.c_custkey=o.o_custkey
    JOIN lineitem l ON l.l_orderkey=o.o_orderkey
    WHERE
    c.c_mktsegment='BUILDING'
    AND o.o_orderdate < DATE '{d}'
    AND l.l_shipdate > DATE '{d}'
    """

query_map = {
    "query1": query1,
    "query2": query2,
    "query3": query3
}

# hint loading

def load_hint(date):

    path = os.path.join(PLAN_DIR, f"{date}.json")

    with open(path) as f:
        plan = json.load(f)

    plan_str = json.dumps(plan)

    hints = []

    if "Seq Scan" in plan_str:
        hints.append("SeqScan(lineitem)")

    if "Bitmap Heap Scan" in plan_str:
        hints.append("BitmapScan(lineitem)")

    if "Index Scan" in plan_str:
        hints.append("IndexScan(lineitem idx_lineitem_shipdate)")

    if "Hash Join" in plan_str:
        hints.append("HashJoin")

    if "Nested Loop" in plan_str:
        hints.append("NestLoop")

    if "Merge Join" in plan_str:
        hints.append("MergeJoin")

    return "/*+ " + " ".join(hints) + " */"
# runtime measureemnt

def runtime_hint(query, hint):

    sql = f"EXPLAIN ANALYZE {hint} {query}"

    cur.execute(sql)

    rows = cur.fetchall()

    for r in rows:
        line = r[0]
        if "Execution Time" in line:
            return float(line.split()[2])

# binary search for optimal switch

def find_switch(qfunc, start, end, Pi_hint, Pj_hint):

    left = start
    right = end

    while (right - left).days > 1:

        mid = left + (right - left) // 2

        q = qfunc(mid)

        rt_pi = runtime_hint(q, Pi_hint)
        rt_pj = runtime_hint(q, Pj_hint)

        if rt_pj < rt_pi:
            right = mid
        else:
            left = mid

    return left, right

# verify switch

def verify(qfunc, qi, qj, Pi_hint, Pj_hint):

    qi_query = qfunc(qi)
    qj_query = qfunc(qj)

    rt_pi_qi = runtime_hint(qi_query, Pi_hint)
    rt_pj_qj = runtime_hint(qj_query, Pj_hint)

    rt_pi_qj = runtime_hint(qj_query, Pi_hint)
    rt_pj_qi = runtime_hint(qi_query, Pj_hint)

    return rt_pi_qi, rt_pj_qj, rt_pi_qj, rt_pj_qi

# incorrect switches from task 3

incorrect_switches = [

("query1","1992-01-07","1992-01-08","DELAYED"),
("query1","1992-01-27","1992-01-28","DELAYED"),
("query1","1992-03-29","1992-03-30","EARLY"),

("query2","1992-05-09","1992-05-10","DELAYED"),
("query2","1992-05-10","1992-05-11","DELAYED"),
("query2","1997-12-19","1997-12-20","EARLY"),

("query3","1992-01-04","1992-01-05","EARLY"),
("query3","1992-01-20","1992-01-21","DELAYED"),
("query3","1992-02-06","1992-02-07","EARLY"),
("query3","1992-05-11","1992-05-12","EARLY"),
("query3","1998-09-02","1998-09-03","DELAYED"),
("query3","1998-11-03","1998-11-04","EARLY"),
("query3","1998-11-28","1998-11-29","DELAYED"),
("query3","1998-11-30","1998-12-01","DELAYED")
]

# task 4 execution

print("\nTASK4 OPTIMAL SWITCH ANALYSIS\n")

for qname, qi, qj, cls in incorrect_switches:

    qfunc = query_map[qname]

    Pi_hint = load_hint(qi)
    Pj_hint = load_hint(qj)

    qi_date = datetime.strptime(qi, "%Y-%m-%d").date()
    qj_date = datetime.strptime(qj, "%Y-%m-%d").date()

    if cls == "DELAYED":
        start = qi_date - timedelta(days=30)
        end = qi_date
    else:
        start = qj_date
        end = qj_date + timedelta(days=30)

    opt_i, opt_j = find_switch(qfunc, start, end, Pi_hint, Pj_hint)

    rt = verify(qfunc, opt_i, opt_j, Pi_hint, Pj_hint)

    print("Query:", qname)
    print("Optimizer Switch:", qi, "->", qj)
    print("Optimal Switch:", opt_i, "->", opt_j)

    print("RT(Pi',qi'):", rt[0])
    print("RT(Pj',qj'):", rt[1])
    print("RT(Pi',qj'):", rt[2])
    print("RT(Pj',qi'):", rt[3])



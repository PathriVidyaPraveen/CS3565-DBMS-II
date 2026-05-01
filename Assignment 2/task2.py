import psycopg2
import json
import os
from datetime import timedelta

conn = psycopg2.connect(
    dbname="tpch_db",
    user="vidya",
    host="/var/run/postgresql",
    port="5433"
)

cur = conn.cursor()

PLAN_DIR = "plans"

if not os.path.exists(PLAN_DIR):
    os.makedirs(PLAN_DIR)


def get_plan(query, d, qname):

    cur.execute("EXPLAIN (FORMAT JSON) " + query)

    result = cur.fetchone()[0]

    plan = result[0]["Plan"]

    filename = f"{PLAN_DIR}/{qname}_{d}.json"

    with open(filename, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Saved plan → {filename}")

    return plan


def normalize_plan(plan):

    nodes = []

    def traverse(node):

        nodes.append(node["Node Type"])

        if "Plans" in node:
            for p in node["Plans"]:
                traverse(p)

    traverse(plan)

    return nodes


def same_plan(p1, p2):
    return normalize_plan(p1) == normalize_plan(p2)


def query1(d):

    return f"""
    SELECT
    SUM(l_quantity),
    SUM(l_extendedprice),
    SUM(l_extendedprice * (1 - l_discount)),
    SUM(l_extendedprice * (1 - l_discount) * (1 + l_tax)),
    AVG(l_quantity),
    AVG(l_extendedprice),
    AVG(l_discount),
    COUNT(*)
    FROM lineitem
    WHERE l_shipdate <= DATE '{d}';
    """


def query2(d):

    return f"""
    SELECT
    o_orderpriority,
    count(*) AS order_count
    FROM orders
    WHERE
    o_orderdate >= DATE '1992-01-01'
    AND o_orderdate < DATE '{d}'
    AND EXISTS (
        SELECT 1
        FROM lineitem
        WHERE l_orderkey = o_orderkey
        AND l_commitdate < l_receiptdate
    )
    GROUP BY o_orderpriority;
    """


def query3(d):

    return f"""
    SELECT
    l.l_orderkey,
    l.l_extendedprice * (1 - l.l_discount) AS revenue,
    o.o_orderdate,
    o.o_shippriority
    FROM
    customer c
    JOIN orders o ON c.c_custkey = o.o_custkey
    JOIN lineitem l ON l.l_orderkey = o.o_orderkey
    WHERE
    c.c_mktsegment = 'BUILDING'
    AND o.o_orderdate < DATE '{d}'
    AND l.l_shipdate > DATE '{d}';
    """


def find_switches(qfunc, start, end, qname):

    switches = []

    def search(left, right):

        plan_left = get_plan(qfunc(left), left, qname)
        plan_right = get_plan(qfunc(right), right, qname)

        if same_plan(plan_left, plan_right):
            return

        if (right - left).days <= 1:
            switches.append((left, right))
            return

        mid = left + (right - left) // 2

        search(left, mid)
        search(mid, right)

    search(start, end)

    return switches


# Query1 parameter range

cur.execute("SELECT MIN(l_shipdate), MAX(l_shipdate) FROM lineitem;")
q1_start, q1_end = cur.fetchone()


# Query2 parameter range

cur.execute("SELECT MIN(o_orderdate), MAX(o_orderdate) FROM orders;")
q2_start, q2_end = cur.fetchone()


# Query3 parameter range (intersection)

cur.execute("""
SELECT
GREATEST(MIN(o_orderdate), MIN(l_shipdate)),
LEAST(MAX(o_orderdate), MAX(l_shipdate))
FROM orders, lineitem;
""")

q3_start, q3_end = cur.fetchone()


print("Query1 Range:", q1_start, "to", q1_end)
print("Query2 Range:", q2_start, "to", q2_end)
print("Query3 Range:", q3_start, "to", q3_end)


switches_q1 = find_switches(query1, q1_start, q1_end, "query1")

switches_q2 = find_switches(query2, q2_start, q2_end, "query2")

switches_q3 = find_switches(query3, q3_start, q3_end, "query3")


with open("output.txt", "w") as f:

    f.write("Query 1:\n")
    for i, (d1, d2) in enumerate(switches_q1):
        f.write(f"Plan Switch {i+1}: {d1} and {d2}\n")

    f.write("\nQuery 2:\n")
    for i, (d1, d2) in enumerate(switches_q2):
        f.write(f"Plan Switch {i+1}: {d1} and {d2}\n")

    f.write("\nQuery 3:\n")
    for i, (d1, d2) in enumerate(switches_q3):
        f.write(f"Plan Switch {i+1}: {d1} and {d2}\n")


print("Plan switch detection completed")
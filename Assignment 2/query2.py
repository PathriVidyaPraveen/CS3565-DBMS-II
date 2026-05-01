import psycopg2
import json
import time
import os

PLAN_DIR="../Task2/plans"

switches=[
("1992-05-09","1992-05-10"),
("1992-05-10","1992-05-11"),
("1997-12-19","1997-12-20")
]

conn=psycopg2.connect(
dbname="tpch_db",
user="postgres",
password="mypassword",
host="localhost",
port="5432"
)

cur=conn.cursor()

def query(d):
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

def generate_query2_hints(plan_json):
    hint_parts=[]
    plan_str=json.dumps(plan_json)

    if "Hash Join" in plan_str:
        hint_parts.append("HashJoin(o l)")
    if "Nested Loop" in plan_str:
        hint_parts.append("NestLoop(o l)")
    if "Merge Join" in plan_str:
        hint_parts.append("MergeJoin(o l)")

    if "idx_orders_orderdate" in plan_str:
        hint_parts.append("IndexScan(o idx_orders_orderdate)")

    if '"Parallel Aware": true' in plan_str:
        hint_parts.append("Parallel(o 4) Parallel(l 4)")

    hint_parts.append("Leading(o l)")

    return f"/*+ {' '.join(hint_parts)} */"

def load_hint(date):
    with open(os.path.join(PLAN_DIR,f"{date}.json")) as f:
        plan=json.load(f)
    return generate_query2_hints(plan)

def runtime(q):
    start=time.time()
    cur.execute(q)
    cur.fetchall()
    end=time.time()
    return (end-start)*1000

def runtime_hint(q,hint):
    sql=f"EXPLAIN ANALYZE {hint} {q}"
    cur.execute(sql)
    rows=cur.fetchall()
    for r in rows:
        if "Execution Time" in r[0]:
            return float(r[0].split()[2])

def classify(pi_qi,pj_qj,pi_qj,pj_qi):
    if pi_qj < pj_qj:
        return "DELAYED"
    if pj_qi < pi_qi:
        return "EARLY"
    return "CORRECT"

print("\nQUERY2 TASK3 RESULTS\n")

for qi,qj in switches:

    qi_query=query(qi)
    qj_query=query(qj)

    Pi_hint=load_hint(qi)
    Pj_hint=load_hint(qj)

    rt_pi_qi=runtime(qi_query)
    rt_pj_qj=runtime(qj_query)

    rt_pi_qj=runtime_hint(qj_query,Pi_hint)
    rt_pj_qi=runtime_hint(qi_query,Pj_hint)

    result=classify(rt_pi_qi,rt_pj_qj,rt_pi_qj,rt_pj_qi)

    print(qi,"->",qj)
    print(rt_pi_qi,rt_pj_qj,rt_pi_qj,rt_pj_qi,result)

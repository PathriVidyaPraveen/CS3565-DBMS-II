import psycopg2
import json
import time
import os

PLAN_DIR="../Task2/plans"

switches=[
("1992-01-04","1992-01-05"),
("1992-01-20","1992-01-21"),
("1992-02-06","1992-02-07"),
("1992-05-11","1992-05-12"),
("1998-09-02","1998-09-03"),
("1998-11-03","1998-11-04"),
("1998-11-15","1998-11-16"),
("1998-11-21","1998-11-22"),
("1998-11-28","1998-11-29"),
("1998-11-30","1998-12-01")
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

def generate_query3_hints(plan_json):

    hint_parts=[]
    plan_str=json.dumps(plan_json)

    if "Hash Join" in plan_str:
        hint_parts.append("HashJoin(c o l)")
    if "Nested Loop" in plan_str:
        hint_parts.append("NestLoop(c o l)")
    if "Merge Join" in plan_str:
        hint_parts.append("MergeJoin(c o l)")

    if '"Parallel Aware": true' in plan_str:
        hint_parts.append("Parallel(l 4) Parallel(o 4)")

    if "idx_orders_orderdate" in plan_str:
        hint_parts.append("IndexScan(o idx_orders_orderdate)")

    hint_parts.append("Leading(c o l)")

    return f"/*+ {' '.join(hint_parts)} */"

def load_hint(date):
    with open(os.path.join(PLAN_DIR,f"{date}.json")) as f:
        plan=json.load(f)
    return generate_query3_hints(plan)

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

print("\nQUERY3 TASK3 RESULTS\n")

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

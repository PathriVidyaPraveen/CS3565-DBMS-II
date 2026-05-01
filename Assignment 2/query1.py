import psycopg2
import json
import time
import os
import statistics

PLAN_DIR = "../Task2/plans"

switches = [
("1992-01-07","1992-01-08"),
("1992-01-27","1992-01-28"),
("1992-03-29","1992-03-30")
]

conn = psycopg2.connect(
    dbname="tpch_db",
    user="postgres",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()


def query(d):
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


def generate_query1_hints(plan_json):

    hint_parts=[]
    plan_str=json.dumps(plan_json)

    if "Seq Scan" in plan_str:
        hint_parts.append("SeqScan(lineitem)")

    if "Index Scan" in plan_str and "idx_lineitem_shipdate" in plan_str:
        hint_parts.append("IndexScan(lineitem idx_lineitem_shipdate)")

    if "Index Only Scan" in plan_str:
        hint_parts.append("IndexOnlyScan(lineitem idx_lineitem_shipdate)")

    if "Bitmap Heap Scan" in plan_str:
        hint_parts.append("BitmapScan(lineitem)")

    if '"Parallel Aware": true' in plan_str:
        hint_parts.append("Parallel(lineitem 4)")

    return f"/*+ {' '.join(hint_parts)} */"


def load_hint(date):

    with open(os.path.join(PLAN_DIR,f"{date}.json")) as f:
        plan=json.load(f)

    return generate_query1_hints(plan)


# avg run time without hint

def runtime_avg(q, runs=100):

    times=[]

    for _ in range(runs):

        start=time.time()

        cur.execute(q)
        cur.fetchall()

        end=time.time()

        times.append((end-start)*1000)

    return statistics.mean(times)


# ang runtime with hint

def runtime_hint_avg(q,hint,runs=10):

    times=[]

    for _ in range(runs):

        sql=f"EXPLAIN ANALYZE {hint} {q}"

        cur.execute(sql)

        rows=cur.fetchall()

        for r in rows:
            if "Execution Time" in r[0]:
                times.append(float(r[0].split()[2]))

    return statistics.mean(times)


def classify(pi_qi,pj_qj,pi_qj,pj_qi):

    if pi_qj < pj_qj:
        return "DELAYED"

    if pj_qi < pi_qi:
        return "EARLY"

    return "CORRECT"


print("\nQUERY1 TASK3 RESULTS (10 RUN AVERAGE)\n")


for qi,qj in switches:

    qi_query=query(qi)
    qj_query=query(qj)

    Pi_hint=load_hint(qi)
    Pj_hint=load_hint(qj)

    rt_pi_qi = runtime_avg(qi_query,100)
    rt_pj_qj = runtime_avg(qj_query,100)

    rt_pi_qj = runtime_hint_avg(qj_query,Pi_hint,100)
    rt_pj_qi = runtime_hint_avg(qi_query,Pj_hint,100)

    result=classify(rt_pi_qi,rt_pj_qj,rt_pi_qj,rt_pj_qi)

    print(qi,"->",qj)

    print("RT(Pi,qi):",rt_pi_qi)
    print("RT(Pj,qj):",rt_pj_qj)
    print("RT(Pi,qj):",rt_pi_qj)
    print("RT(Pj,qi):",rt_pj_qi)

    print("CLASS:",result)

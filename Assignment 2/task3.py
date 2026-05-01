import psycopg2
import json
import statistics

# database connection
conn = psycopg2.connect(
    dbname="tpch_db",
    user="postgres",
    password="mypassword",
    host="localhost",
    port="5432"
)

conn.autocommit = True
cur = conn.cursor()

# queries

queries = {

"Query1": """
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
WHERE l_shipdate <= %s
""",

"Query2": """
SELECT o_orderpriority, count(*) AS order_count
FROM orders
WHERE
o_orderdate >= DATE '1992-01-01'
AND o_orderdate < %s
AND EXISTS (
SELECT 1
FROM lineitem
WHERE l_orderkey=o_orderkey
AND l_commitdate<l_receiptdate
)
GROUP BY o_orderpriority
""",

"Query3": """
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
AND o.o_orderdate < %s
AND l.l_shipdate > %s
"""
}

# plan switches

plan_switches = {

"Query1":[
("1992-01-07","1992-01-08"),
("1992-01-27","1992-01-28"),
("1992-03-29","1992-03-30")
],

"Query2":[
("1992-05-09","1992-05-10"),
("1992-05-10","1992-05-11"),
("1997-12-19","1997-12-20")
],

"Query3":[
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
}


def get_plan(query,params):

    cur.execute("EXPLAIN (FORMAT JSON) "+query,params)

    result = cur.fetchone()[0]

    return result[0]["Plan"]

# build operator tree

def extract_tree(node):

    tree = {
        "NodeType": node.get("Node Type"),
        "Relation": node.get("Relation Name"),
        "Alias": node.get("Alias"),
        "Index": node.get("Index Name"),
        "JoinType": node.get("Join Type"),
        "Strategy": node.get("Strategy"),
        "Workers": node.get("Workers Planned"),
        "Parallel": node.get("Parallel Aware"),
        "Children":[]
    }

    for child in node.get("Plans",[]):
        tree["Children"].append(extract_tree(child))

    return tree

# collect tables

def collect_tables(node):

    tables=[]

    if node.get("Relation"):
        tables.append(node.get("Alias",node["Relation"]))

    for c in node["Children"]:
        tables.extend(collect_tables(c))

    return tables

# parallel detection

def has_parallel(node):

    if node["NodeType"] in ("Gather","Gather Merge"):
        return True

    for c in node["Children"]:
        if has_parallel(c):
            return True

    return False


def get_workers(node):

    if node["NodeType"] in ("Gather","Gather Merge"):
        return node.get("Workers",2)

    for c in node["Children"]:
        w = get_workers(c)
        if w:
            return w

    return None

# extract hints

def extract_hints(node,hints=None):

    if hints is None:
        hints=[]

    t=node["NodeType"]

    if node.get("Relation"):

        alias=node.get("Alias",node["Relation"])

        if t=="Seq Scan":
            hints.append(f"SeqScan({alias})")

        elif t=="Index Scan":
            idx=node.get("Index")
            if idx:
                hints.append(f"IndexScan({alias} {idx})")
            else:
                hints.append(f"IndexScan({alias})")

        elif t=="Index Only Scan":
            hints.append(f"IndexOnlyScan({alias})")

        elif t=="Bitmap Heap Scan":
            hints.append(f"BitmapScan({alias})")

    if t in ("Hash Join","Nested Loop","Merge Join"):

        tables=[]
        for c in node["Children"]:
            tables.extend(collect_tables(c))

        if tables:

            if t=="Hash Join":
                hints.append(f"HashJoin({' '.join(tables)})")

            elif t=="Nested Loop":
                hints.append(f"NestLoop({' '.join(tables)})")

            elif t=="Merge Join":
                hints.append(f"MergeJoin({' '.join(tables)})")

    for c in node["Children"]:
        extract_hints(c,hints)

    return hints

# leading join order

def build_leading(node):

    if node.get("Relation"):
        return node.get("Alias",node["Relation"])

    if node["NodeType"] in ("Hash Join","Nested Loop","Merge Join"):

        if len(node["Children"])==2:

            left = build_leading(node["Children"][0])
            right = build_leading(node["Children"][1])

            return f"({left} {right})"

    for c in node["Children"]:
        x = build_leading(c)
        if x:
            return x

    return ""


def build_hint(plan):

    tree = extract_tree(plan)

    hints = list(dict.fromkeys(extract_hints(tree)))

    leading = build_leading(tree)

    if leading and "(" in leading:
        hints.append(f"Leading({leading})")

    if has_parallel(tree):

        workers = get_workers(tree)
        tables = list(set(collect_tables(tree)))

        for t in tables:
            hints.append(f"Parallel({t} {workers} hard)")

    else:

        tables = list(set(collect_tables(tree)))

        for t in tables:
            hints.append(f"Parallel({t} 0 hard)")

    return "/*+ "+" ".join(hints)+" */"


def run_query(query,params,hint="",runs=5):

    if hint:
        sql = hint+"\nEXPLAIN (ANALYZE,FORMAT JSON) "+query
    else:
        sql = "EXPLAIN (ANALYZE,FORMAT JSON) "+query

    times=[]

    for _ in range(runs):

        cur.execute(sql,params)

        result = cur.fetchone()[0][0]

        t = result.get("Execution Time")

        times.append(t)

    return statistics.median(times)

# classification

def classify(pi_qi,pj_qj,pi_qj,pj_qi):

    if pj_qi < pi_qi:
        return "DELAYED"

    if pi_qj < pj_qj:
        return "EARLY"

    return "CORRECT"

# main function

for query_name in plan_switches:

    print("\n",query_name)

    query = queries[query_name]

    for i,(qi,qj) in enumerate(plan_switches[query_name]):

        params_i = (qi,qi) if query_name=="Query3" else (qi,)
        params_j = (qj,qj) if query_name=="Query3" else (qj,)

        plan_i = get_plan(query,params_i)
        plan_j = get_plan(query,params_j)

        hint_pi = build_hint(plan_i)
        hint_pj = build_hint(plan_j)

        rt_pi_qi = run_query(query,params_i)
        rt_pj_qj = run_query(query,params_j)

        rt_pi_qj = run_query(query,params_j,hint_pi)
        rt_pj_qi = run_query(query,params_i,hint_pj)

        c = classify(rt_pi_qi,rt_pj_qj,rt_pi_qj,rt_pj_qi)

        print(f"Switch {i+1}: {qi} -> {qj}")
        print("hint_pi:",hint_pi)
        print("hint_pj:",hint_pj)

        print(
        f"RT(Pi,qi)={rt_pi_qi:.3f}  "
        f"RT(Pj,qj)={rt_pj_qj:.3f}  "
        f"RT(Pi,qj)={rt_pi_qj:.3f}  "
        f"RT(Pj,qi)={rt_pj_qi:.3f}"
        )

        print("CLASS:",c,"\n")

cur.close()
conn.close()

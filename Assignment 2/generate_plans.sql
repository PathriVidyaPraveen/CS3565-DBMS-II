SET max_parallel_workers_per_gather = 0;

EXPLAIN (FORMAT JSON)
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
WHERE l_shipdate <= DATE '1992-01-05'
\g 1992-01-05.json


EXPLAIN (FORMAT JSON)
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
WHERE l_shipdate <= DATE '1993-01-05'
\g 1993-01-05.json


EXPLAIN (FORMAT JSON)
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
WHERE l_shipdate <= DATE '1994-01-05'
\g 1994-01-05.json


EXPLAIN (FORMAT JSON)
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
WHERE l_shipdate <= DATE '1995-01-05'
\g 1995-01-05.json
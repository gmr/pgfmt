SELECT x, (SELECT MAX(y) FROM t2 WHERE t2.id = t1.id) AS max_y FROM t1 WHERE z = 1

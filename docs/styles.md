# Style Reference

pgfmt supports seven formatting styles. Each style is based on a
well-known SQL style guide.

## river

Based on [sqlstyle.guide](https://www.sqlstyle.guide/) by Simon Holywell.

Keywords are right-aligned to form a visual "river" separating keywords
from content. INNER/LEFT/RIGHT/FULL JOINs are content-indented on the
right side of the river. Plain `JOIN` is a river keyword.

```sql
SELECT r.last_name,
       (SELECT MAX(year)
          FROM champions AS c
         WHERE c.last_name = r.last_name) AS last_year
  FROM riders AS r
       INNER JOIN bikes AS b
       ON r.bike_vin_num = b.vin_num
          AND b.engines > 2
 WHERE r.last_name IN ('Smith', 'Jones')
    OR r.rank = 1
 ORDER BY r.last_name;
```

## aweber

Based on river style with JOINs as river keywords. INNER JOIN, LEFT JOIN,
etc. participate in the river alignment alongside SELECT, FROM, WHERE.

```sql
    SELECT r.last_name
      FROM riders AS r
INNER JOIN bikes AS b
        ON r.bike_vin_num = b.vin_num
       AND b.engines > 2
 ORDER BY r.last_name;
```

## mattmc3

Based on the [Modern SQL Style Guide](https://github.com/mattmc3/sql-style-guide).
Lowercase river with leading commas. Uses plain `join` instead of
`inner join`.

```sql
select p.name as product_name
     , p.product_number
     , pm.name as model_name
  from production.product as p
  join production.product_model as pm
    on p.product_model_id = pm.product_model_id
 where p.color in ('Blue', 'Red')
   and p.list_price < 800.00
 order by p.name;
```

## mozilla

Based on the [Mozilla SQL Style Guide](https://docs.telemetry.mozilla.org/concepts/sql_style).
Keywords left-aligned at column 0, content indented 4 spaces. One item
per line. AND/OR at start of line.

```sql
SELECT
    a.title,
    COUNT(*) AS cnt
FROM albums AS a
WHERE
    a.title = 'Charcoal Lane'
    AND a.year > 2000
GROUP BY a.title
HAVING
    COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 10;
```

## dbt

Based on [dbt Labs' SQL style](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql).
Lowercase keywords, 4-space indent, blank lines between clauses.
Explicit join types.

```sql
select
    a.title,
    count(*) as cnt

from albums as a

where
    a.title = 'Charcoal Lane'
    and a.year > 2000

group by a.title

having
    count(*) > 1

order by cnt desc

limit 10
```

## gitlab

Based on the [GitLab SQL Style Guide](https://handbook.gitlab.com/handbook/enterprise-data/platform/sql-style-guide/).
Uppercase keywords, 2-space indent. Blank lines inside CTE bodies.

```sql
SELECT
  a.title,
  COUNT(*) AS cnt
FROM albums AS a
WHERE
  a.title = 'Charcoal Lane'
  AND a.year > 2000
GROUP BY a.title
HAVING
  COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 10;
```

## kickstarter

Based on the [Kickstarter SQL Style Guide](https://gist.github.com/fredbenenson/7bb92718e19138c20591).
Uppercase keywords, 2-space indent. JOIN and ON on the same line,
additional conditions indented. Compact CTE chaining.

```sql
SELECT
  a.title,
  COUNT(*) AS cnt
FROM albums AS a
INNER JOIN orders AS o ON a.id = o.album_id
WHERE
  a.title = 'Charcoal Lane'
  AND a.year > 2000
GROUP BY a.title
ORDER BY cnt DESC
LIMIT 10;
```

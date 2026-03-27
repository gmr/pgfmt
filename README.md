# pgfmt

A PostgreSQL SQL formatter with multiple style options.

[![Version](https://img.shields.io/pypi/v/pgfmt.svg?)](https://pypi.org/project/pgfmt)
[![Testing](https://github.com/gmr/pgfmt/actions/workflows/testing.yaml/badge.svg)](https://github.com/gmr/pgfmt/actions/workflows/testing.yaml)
[![Coverage](https://codecov.io/gh/gmr/pgfmt/branch/main/graph/badge.svg)](https://codecov.io/github/gmr/pgfmt?branch=main)
[![License](https://img.shields.io/pypi/l/pgfmt.svg?)](https://github.com/gmr/pgfmt/blob/main/LICENSE)

pgfmt parses SQL using [pgparse](https://github.com/gmr/pgparse) (PostgreSQL's
own parser via libpg_query) and reformats it according to one of several
well-known style guides.

## Installation

```bash
pip install pgfmt
```

## CLI Usage

```bash
# Format a file (default: river style)
pgfmt query.sql

# Format from stdin
echo "SELECT a,b FROM t WHERE x=1" | pgfmt

# Choose a style
pgfmt --style mozilla query.sql
pgfmt --style dbt query.sql

# Check if already formatted (exit 1 if not)
pgfmt --check query.sql
```

## Library Usage

```python
import pgfmt

sql = "SELECT a, b FROM my_table WHERE x = 1 AND y = 2"

# Default (river) style
print(pgfmt.format(sql))

# Choose a style
print(pgfmt.format(sql, style='mozilla'))
print(pgfmt.format(sql, style='dbt'))
```

## Styles

### river (default)

Based on [sqlstyle.guide](https://www.sqlstyle.guide/) by Simon Holywell.
Keywords are right-aligned to form a visual "river" separating keywords from
content. Uppercase keywords.

```sql
SELECT a.title,
       a.release_date
  FROM albums AS a
 WHERE a.title = 'Charcoal Lane'
    OR a.title = 'The New Danger';
```

### mozilla

Based on the [Mozilla SQL Style Guide](https://docs.telemetry.mozilla.org/concepts/sql_style).
Keywords left-aligned at column 0, content indented 4 spaces underneath.
One item per line. Uppercase keywords.

```sql
SELECT
    a.title,
    a.release_date
FROM albums AS a
WHERE
    a.title = 'Charcoal Lane'
    OR a.title = 'The New Danger';
```

### aweber

Based on river style with JOINs as river keywords. INNER JOIN, LEFT JOIN,
etc. participate in river alignment. Uppercase keywords.

```sql
    SELECT r.last_name
      FROM riders AS r
INNER JOIN bikes AS b
        ON r.bike_vin_num = b.vin_num
       AND b.engines > 2;
```

### dbt

Based on [dbt Labs' SQL style](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql).
Lowercase keywords, 4-space indent, blank lines between clauses, generous
whitespace. Explicit join types.

```sql
select
    a.title,
    a.release_date

from albums as a

where
    a.title = 'Charcoal Lane'
    or a.title = 'The New Danger'
```

### gitlab

Based on the [GitLab SQL Style Guide](https://handbook.gitlab.com/handbook/enterprise-data/platform/sql-style-guide/).
Uppercase keywords, 2-space indent, blank lines inside CTE bodies.

```sql
SELECT
  a.title,
  a.release_date
FROM albums AS a
WHERE
  a.title = 'Charcoal Lane'
  OR a.title = 'The New Danger';
```

### kickstarter

Based on the [Kickstarter SQL Style Guide](https://gist.github.com/fredbenenson/7bb92718e19138c20591).
Uppercase keywords, 2-space indent, JOIN ON on same line, compact CTE chaining.

```sql
SELECT
  a.title,
  a.release_date
FROM albums AS a
INNER JOIN orders AS o ON a.id = o.album_id
WHERE
  a.title = 'Charcoal Lane'
  AND a.year > 2000;
```

### mattmc3

Based on the [Modern SQL Style Guide](https://github.com/mattmc3/sql-style-guide)
by mattmc3. Lowercase river-style with leading commas. Uses plain `join`
instead of `inner join`.

```sql
select a.title
     , a.release_date
  from albums as a
  join orders as o
    on a.id = o.album_id
 where a.title = 'Charcoal Lane'
   and a.year > 2000;
```

## Supported Statements

- `SELECT` (with JOINs, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET,
  DISTINCT, DISTINCT ON, UNION/INTERSECT/EXCEPT, subqueries, CTEs)
- `INSERT` (VALUES, INSERT ... SELECT)
- `UPDATE`
- `DELETE`
- `CREATE TABLE` (columns, constraints, WITH storage options)
- `CREATE FOREIGN TABLE` (SERVER, OPTIONS)
- `CREATE VIEW` / `CREATE MATERIALIZED VIEW`
- `CREATE FUNCTION`
- `CREATE DOMAIN`
- Unsupported DDL passes through with normalized whitespace

# pgfmt

A PostgreSQL SQL formatter with multiple style options.

[![Testing](https://github.com/gmr/pgfmt/actions/workflows/testing.yaml/badge.svg)](https://github.com/gmr/pgfmt/actions/workflows/testing.yaml)
[![License](https://img.shields.io/github/license/gmr/pgfmt)](https://github.com/gmr/pgfmt/blob/main/LICENSE)

pgfmt parses SQL using [tree-sitter-postgres](https://github.com/nicholasgasior/tree-sitter-postgres)
and reformats it according to one of several well-known style guides.
Formatting is powered by [libpgfmt](https://crates.io/crates/libpgfmt).

## Installation

### Homebrew (macOS / Linux)

```bash
brew tap gmr/pgfmt
brew install pgfmt
```

### Quick Install (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/gmr/pgfmt/main/install.sh | sh
```

To install to a custom directory:

```bash
INSTALL_DIR=~/.local/bin curl -fsSL https://raw.githubusercontent.com/gmr/pgfmt/main/install.sh | sh
```

### Install a Specific Version

```bash
VERSION=v1.0.0 curl -fsSL https://raw.githubusercontent.com/gmr/pgfmt/main/install.sh | sh
```

### From Source (via Cargo)

```bash
cargo install pgfmt
```

### Download Binaries

Pre-built binaries for Linux and macOS (x86_64 and aarch64) are available on
the [GitHub Releases](https://github.com/gmr/pgfmt/releases) page.

## Usage

```bash
# Format a file (default: aweber style)
pgfmt query.sql

# Format from stdin
echo "SELECT a,b FROM t WHERE x=1" | pgfmt

# Choose a style
pgfmt --style mozilla query.sql
pgfmt --style dbt query.sql

# Check if already formatted (exit 1 if not)
pgfmt --check query.sql
```

## Styles

| Style | Based On |
|-------|----------|
| aweber (default) | [AWeber SQL Style Guide](https://gist.github.com/gmr/2cceb85bb37be96bc96f05c5b8de9e1b) |
| dbt | [How we style our SQL](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql) by dbt Labs |
| gitlab | [GitLab SQL Style Guide](https://handbook.gitlab.com/handbook/enterprise-data/platform/sql-style-guide/) |
| kickstarter | [Kickstarter SQL Style Guide](https://gist.github.com/fredbenenson/7bb92718e19138c20591) by Fred Benenson |
| mattmc3 | [Modern SQL Style Guide](https://gist.github.com/mattmc3/38a85e6a4ca1093816c08d4815fbebfb) by mattmc3 |
| mozilla | [Mozilla SQL Style Guide](https://docs.telemetry.mozilla.org/concepts/sql_style) |
| river | [SQL Style Guide](https://www.sqlstyle.guide/) by Simon Holywell |

### aweber (default)

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

Based on the [Modern SQL Style Guide](https://gist.github.com/mattmc3/38a85e6a4ca1093816c08d4815fbebfb)
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

### river

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

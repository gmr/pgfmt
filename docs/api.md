# Python API

pgfmt can be used as a library in Python applications.

## `pgfmt.format`

::: pgfmt.format

## Usage

```python
import pgfmt

# Format with the default style (river)
result = pgfmt.format("SELECT a, b FROM t WHERE x = 1")
print(result)
```

Output:

```sql
SELECT a,
       b
  FROM t
 WHERE x = 1;
```

### Choosing a style

```python
import pgfmt

sql = "SELECT a, b FROM t WHERE x = 1 AND y = 2"

# Mozilla style
print(pgfmt.format(sql, style='mozilla'))

# dbt style
print(pgfmt.format(sql, style='dbt'))

# mattmc3 style (lowercase river with leading commas)
print(pgfmt.format(sql, style='mattmc3'))
```

### Available styles

- `'river'` - Right-aligned keyword river (default)
- `'aweber'` - River with JOINs as river keywords
- `'mattmc3'` - Lowercase river with leading commas
- `'mozilla'` - Left-aligned keywords, 4-space indent
- `'dbt'` - Lowercase mozilla with blank lines between clauses
- `'gitlab'` - Left-aligned keywords, 2-space indent
- `'kickstarter'` - Left-aligned keywords, 2-space indent, ON same line as JOIN

### Error handling

```python
import pgparse
import pgfmt

# Invalid SQL raises pgparse.PGQueryError
try:
    pgfmt.format("SELEC broken")
except pgparse.PGQueryError as e:
    print(f"Parse error: {e.message} at position {e.position}")

# Unknown style raises ValueError
try:
    pgfmt.format("SELECT 1", style='unknown')
except ValueError as e:
    print(e)  # "Unsupported style: 'unknown'"
```

### Multi-statement input

`pgfmt.format` handles multiple semicolon-delimited statements,
returning them separated by blank lines:

```python
import pgfmt

sql = "SELECT 1; SELECT 2; SELECT 3"
print(pgfmt.format(sql))
```

Output:

```sql
SELECT 1;

SELECT 2;

SELECT 3;
```

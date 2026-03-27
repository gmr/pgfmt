# pgfmt

A PostgreSQL SQL formatter with multiple style options.

pgfmt parses SQL using [pgparse](https://github.com/gmr/pgparse) (PostgreSQL's
own parser via libpg_query) and reformats it according to one of several
well-known style guides.

## Installation

```bash
pip install pgfmt
```

## Quick Start

```bash
# Format a file
pgfmt query.sql

# Format from stdin
echo "SELECT a,b FROM t WHERE x=1" | pgfmt

# Choose a style
pgfmt --style dbt query.sql
```

```python
import pgfmt

formatted = pgfmt.format("SELECT a, b FROM t WHERE x = 1")
```

## Available Styles

| Style | Keywords | Layout | Commas | Indent |
|-------|----------|--------|--------|--------|
| [river](styles.md#river) (default) | UPPERCASE | Right-aligned river | trailing | river |
| [aweber](styles.md#aweber) | UPPERCASE | River, JOINs in river | trailing | river |
| [mattmc3](styles.md#mattmc3) | lowercase | River, leading commas | leading | river |
| [mozilla](styles.md#mozilla) | UPPERCASE | Left-aligned | trailing | 4-space |
| [dbt](styles.md#dbt) | lowercase | Left-aligned, blank lines | trailing | 4-space |
| [gitlab](styles.md#gitlab) | UPPERCASE | Left-aligned | trailing | 2-space |
| [kickstarter](styles.md#kickstarter) | UPPERCASE | Left-aligned, ON same line | trailing | 2-space |

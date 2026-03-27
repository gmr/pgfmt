# CLI Reference

pgfmt provides a command-line interface for formatting SQL files or stdin.

## Usage

```
pgfmt [--style STYLE] [--check] [files ...]
```

## Arguments

### `files`

One or more SQL files to format. If no files are given, pgfmt reads from
stdin.

```bash
# Format a single file
pgfmt query.sql

# Format multiple files
pgfmt schema.sql queries.sql

# Format from stdin
echo "SELECT a,b FROM t" | pgfmt

# Pipe from another command
pg_dump mydb | pgfmt --style mozilla > formatted.sql
```

### `--style`

Choose a formatting style. Default is `river`.

Available styles: `river`, `mozilla`, `aweber`, `dbt`, `gitlab`,
`kickstarter`, `mattmc3`

```bash
pgfmt --style dbt query.sql
pgfmt --style mozilla query.sql
pgfmt --style mattmc3 query.sql
```

### `--check`

Check if files are already formatted without modifying them. Exits with
code 1 if any file would be reformatted, 0 if all files are already
formatted. Useful in CI pipelines.

```bash
# Check formatting in CI
pgfmt --check --style dbt models/*.sql

# Use in a pre-commit hook or Makefile
pgfmt --check query.sql || echo "Needs formatting"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (or all files already formatted with `--check`) |
| 1 | Files would be reformatted (`--check` mode) |

## Examples

### Format a file in place

pgfmt writes to stdout, so use shell redirection or `sponge` to format
in place:

```bash
# Using a temp file
pgfmt query.sql > query.formatted.sql && mv query.formatted.sql query.sql

# Using sponge (from moreutils)
pgfmt query.sql | sponge query.sql
```

### Multi-statement files

pgfmt handles files with multiple semicolon-delimited statements:

```bash
pgfmt schema.sql
```

Each statement is formatted independently and separated by a blank line.

### Unsupported statements

Statements without a dedicated formatter (e.g., `ALTER TABLE`, `GRANT`,
`CREATE INDEX`) pass through with normalized whitespace.

# pgfmt

A PostgreSQL SQL formatter.

## Development

```bash
uv sync              # Install dependencies
ci/test              # Run linting + tests with coverage
```

## Build System

- **pyproject.toml** with hatchling build backend
- **uv** for dependency management
- **dependency-groups** for dev/docs extras

## Testing

- **pytest** as the test runner
- **coverage** for code coverage reporting
- Tests live in `tests/`

## Code Style

- **ruff** for linting and formatting
- 79 character line length
- Single quotes
- Pre-commit hooks configured

## Key Directories

- `src/pgfmt/` - Main package
- `tests/` - Test suite
- `ci/` - CI scripts

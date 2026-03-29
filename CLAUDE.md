# pgfmt

A PostgreSQL SQL formatter CLI, powered by [libpgfmt](https://crates.io/crates/libpgfmt).

## Development

```bash
just check           # Run formatting, linting, and tests
just build           # Build debug binary
just fmt             # Auto-format code
```

## Build System

- **Cargo.toml** with Rust 2024 edition
- **libpgfmt** for SQL formatting
- **clap** for CLI argument parsing

## Testing

- `cargo test` as the test runner
- Pre-commit hooks run fmt and clippy

## Code Style

- **rustfmt** for formatting
- **clippy** with `-D warnings`
- Pre-commit hooks configured

## Key Files

- `src/main.rs` - CLI binary
- `justfile` - Build/test/release recipes
- `install.sh` - curl-based installer

# Default recipe: run checks
default: check

# Run all checks (format, lint, test)
check: fmt-check lint test

# Build the binary
build:
    cargo build

# Run tests
test:
    cargo test

# Run clippy lints
lint:
    cargo clippy -- -D warnings

# Check formatting
fmt-check:
    cargo fmt --check

# Auto-format code
fmt:
    cargo fmt

# Run all checks then build in release mode
release-build: check
    cargo build --release

# Set the release version in Cargo.toml
set-version version:
    #!/usr/bin/env bash
    set -euo pipefail
    current=$(grep '^version' Cargo.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
    if [ "{{version}}" = "$current" ]; then
        echo "Version is already {{version}}"
        exit 1
    fi
    # Use a temp file for portability (BSD sed -i requires arg, GNU doesn't)
    tmp=$(mktemp)
    sed 's/^version = ".*"/version = "{{version}}"/' Cargo.toml > "$tmp"
    mv "$tmp" Cargo.toml
    cargo check
    echo "Updated version: $current -> {{version}}"

# Tag a release (sets version, commits, tags, pushes)
release version: (set-version version)
    git add Cargo.toml Cargo.lock
    git commit -m "Release v{{version}}"
    git tag -a "v{{version}}" -m "v{{version}}"
    git push origin main --tags

# Publish to crates.io (dry run)
publish-dry:
    cargo publish --dry-run

# Publish to crates.io
publish:
    cargo publish

# Clean build artifacts
clean:
    cargo clean

# Install locally
install:
    cargo install --path .

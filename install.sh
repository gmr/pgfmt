#!/usr/bin/env sh
set -e

REPO="gmr/pgfmt"
BINARY="pgfmt"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"

get_arch() {
    arch=$(uname -m)
    case "$arch" in
        x86_64|amd64) echo "x86_64" ;;
        arm64|aarch64) echo "aarch64" ;;
        *) echo "Unsupported architecture: $arch" >&2; exit 1 ;;
    esac
}

get_os() {
    os=$(uname -s)
    case "$os" in
        Linux) echo "unknown-linux-gnu" ;;
        Darwin) echo "apple-darwin" ;;
        *) echo "Unsupported OS: $os" >&2; exit 1 ;;
    esac
}

main() {
    arch=$(get_arch)
    os=$(get_os)
    target="${arch}-${os}"

    if [ -z "$VERSION" ]; then
        VERSION=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
            | grep '"tag_name"' | head -1 | cut -d'"' -f4)
    fi

    if [ -z "$VERSION" ]; then
        echo "Error: could not determine latest version" >&2
        exit 1
    fi

    url="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY}-${target}.tar.gz"

    echo "Downloading ${BINARY} ${VERSION} for ${target}..."
    tmpdir=$(mktemp -d)
    trap 'rm -rf "$tmpdir"' EXIT

    curl -fsSL "$url" | tar xz -C "$tmpdir"

    echo "Installing to ${INSTALL_DIR}/${BINARY}..."
    if [ -w "$INSTALL_DIR" ]; then
        install "$tmpdir/$BINARY" "$INSTALL_DIR/$BINARY"
    else
        sudo install "$tmpdir/$BINARY" "$INSTALL_DIR/$BINARY"
    fi

    echo "${BINARY} ${VERSION} installed to ${INSTALL_DIR}/${BINARY}"
}

main

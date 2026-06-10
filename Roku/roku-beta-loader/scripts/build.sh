#!/usr/bin/env bash
#
# Cross-compile the roku-beta-loader CLI for Linux, Windows, and macOS.
#
# Usage:
#   scripts/build.sh                 # build the default platform matrix
#   scripts/build.sh linux/amd64     # build one or more specific platforms
#   scripts/build.sh linux/amd64 windows/amd64 darwin/arm64
#
# Environment overrides:
#   VERSION    version string stamped into the binary (default: git describe, else "dev")
#   PLATFORMS  space-separated GOOS/GOARCH list (default matrix below)
#   OUTPUT_DIR output directory (default: dist)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

BIN_NAME="roku-beta-loader"
PKG="./cmd/roku-beta-loader"
OUTPUT_DIR="${OUTPUT_DIR:-dist}"

# Default platform matrix. Override with positional args or $PLATFORMS.
DEFAULT_PLATFORMS=(
  "linux/amd64"
  "linux/arm64"
  "darwin/amd64"
  "darwin/arm64"
  "windows/amd64"
  "windows/arm64"
)

if [[ "$#" -gt 0 ]]; then
  PLATFORMS_LIST=("$@")
elif [[ -n "${PLATFORMS:-}" ]]; then
  # shellcheck disable=SC2206
  PLATFORMS_LIST=(${PLATFORMS})
else
  PLATFORMS_LIST=("${DEFAULT_PLATFORMS[@]}")
fi

# Resolve a version string: explicit env, else git, else "dev".
if [[ -n "${VERSION:-}" ]]; then
  VERSION="$VERSION"
elif git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  VERSION="$(git -C "$PROJECT_ROOT" describe --tags --always --dirty 2>/dev/null || echo dev)"
else
  VERSION="dev"
fi

LDFLAGS="-s -w -X main.version=${VERSION}"

echo "Building ${BIN_NAME} ${VERSION}"
echo "Output: ${OUTPUT_DIR}/"
echo

mkdir -p "$OUTPUT_DIR"

for platform in "${PLATFORMS_LIST[@]}"; do
  GOOS="${platform%%/*}"
  GOARCH="${platform##*/}"
  if [[ "$GOOS" == "$platform" || -z "$GOARCH" ]]; then
    echo "Skipping malformed platform '$platform' (expected GOOS/GOARCH)" >&2
    continue
  fi

  out="${OUTPUT_DIR}/${BIN_NAME}-${GOOS}-${GOARCH}"
  if [[ "$GOOS" == "windows" ]]; then
    out="${out}.exe"
  fi

  echo "  -> ${GOOS}/${GOARCH}"
  CGO_ENABLED=0 GOOS="$GOOS" GOARCH="$GOARCH" \
    go build -trimpath -ldflags "$LDFLAGS" -o "$out" "$PKG"
done

echo
echo "Done. Artifacts in ${OUTPUT_DIR}/:"
ls -1 "$OUTPUT_DIR"

# Generate a checksums file when a SHA-256 tool is available.
checksum_file="${OUTPUT_DIR}/SHA256SUMS"
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUTPUT_DIR" && sha256sum "${BIN_NAME}"-* >"SHA256SUMS")
  echo "Checksums: ${checksum_file}"
elif command -v shasum >/dev/null 2>&1; then
  (cd "$OUTPUT_DIR" && shasum -a 256 "${BIN_NAME}"-* >"SHA256SUMS")
  echo "Checksums: ${checksum_file}"
fi

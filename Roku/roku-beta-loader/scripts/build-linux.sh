#!/usr/bin/env bash
#
# Build the roku-beta-loader CLI (all platforms) and GUI (Linux) on a Linux host.
#
# CLI prerequisites: Go 1.22+
#
# GUI prerequisites:
#   sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.0-dev   # Ubuntu 22.04 / Debian
#   sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.1-dev   # Ubuntu 24.04+ / Pop!_OS 24.04+
#   go install github.com/wailsapp/wails/v2/cmd/wails@latest
#
# Usage:
#   scripts/build-linux.sh             # full build
#   scripts/build-linux.sh --no-gui    # CLI only (skip Wails)
#   VERSION=1.2.3 scripts/build-linux.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

BUILD_GUI=true
if [[ "${1:-}" == "--no-gui" ]]; then
  BUILD_GUI=false
fi

# Resolve version: env override → git → "dev"
if [[ -z "${VERSION:-}" ]]; then
  if git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    VERSION="$(git -C "$PROJECT_ROOT" describe --tags --always --dirty 2>/dev/null || echo dev)"
  else
    VERSION="dev"
  fi
fi
echo "roku-beta-loader ${VERSION}"

# ── CLI: cross-compile for all platforms ─────────────────────────────────────
OUTPUT_DIR="${OUTPUT_DIR:-dist}"
LDFLAGS="-s -w -X main.version=${VERSION}"
echo
echo "Building CLI → ${OUTPUT_DIR}/"
mkdir -p "$OUTPUT_DIR"

PLATFORMS=(linux/amd64 linux/arm64 darwin/amd64 darwin/arm64 windows/amd64 windows/arm64)
for platform in "${PLATFORMS[@]}"; do
  GOOS="${platform%%/*}"
  GOARCH="${platform##*/}"
  out="${OUTPUT_DIR}/roku-beta-loader-${GOOS}-${GOARCH}"
  [[ "$GOOS" == "windows" ]] && out="${out}.exe"
  printf "  %-24s %s\n" "${GOOS}/${GOARCH}" "$out"
  CGO_ENABLED=0 GOOS="$GOOS" GOARCH="$GOARCH" \
    go build -trimpath -ldflags "$LDFLAGS" -o "$out" ./cmd/roku-beta-loader
done

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUTPUT_DIR" && sha256sum roku-beta-loader-* > SHA256SUMS)
  echo "Checksums: ${OUTPUT_DIR}/SHA256SUMS"
fi

# ── GUI: native Linux build via Wails ────────────────────────────────────────
if [[ "$BUILD_GUI" == false ]]; then
  echo; echo "Done (CLI only)."
  exit 0
fi

echo
echo "Building GUI (Linux)..."

if ! command -v wails >/dev/null 2>&1; then
  echo "⚠  wails not found — skipping GUI build."
  echo "   Install: go install github.com/wailsapp/wails/v2/cmd/wails@latest"
  echo; echo "Done (CLI only)."
  exit 0
fi

WAILS_TAGS=""
if pkg-config --exists gtk+-3.0 webkit2gtk-4.0 2>/dev/null; then
  WAILS_TAGS=""
elif pkg-config --exists gtk+-3.0 webkit2gtk-4.1 2>/dev/null; then
  WAILS_TAGS="webkit2_41"
else
  echo "⚠  GTK/WebKit2GTK not found — skipping GUI build."
  echo "   Install one of:"
  echo "     sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.0-dev"
  echo "     sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.1-dev"
  echo; echo "Done (CLI only)."
  exit 0
fi

WAILS_BUILD_ARGS=(-ldflags "-X main.version=${VERSION}")
[[ -n "$WAILS_TAGS" ]] && WAILS_BUILD_ARGS+=(-tags "$WAILS_TAGS")
wails build "${WAILS_BUILD_ARGS[@]}"
echo "GUI binary: build/bin/roku-beta-loader-gui"

echo
echo "Done."

#!/usr/bin/env bash
#
# Build the roku-beta-loader CLI (all platforms) and GUI (macOS) on a macOS host.
#
# CLI prerequisites: Go 1.22+
#
# GUI prerequisites:
#   Xcode Command Line Tools:  xcode-select --install
#   go install github.com/wailsapp/wails/v2/cmd/wails@latest
#
# Usage:
#   scripts/build-mac.sh               # full build
#   scripts/build-mac.sh --no-gui      # CLI only (skip Wails)
#   VERSION=1.2.3 scripts/build-mac.sh
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

if command -v shasum >/dev/null 2>&1; then
  (cd "$OUTPUT_DIR" && shasum -a 256 roku-beta-loader-* > SHA256SUMS)
  echo "Checksums: ${OUTPUT_DIR}/SHA256SUMS"
fi

# ── GUI: native macOS build via Wails ────────────────────────────────────────
if [[ "$BUILD_GUI" == false ]]; then
  echo; echo "Done (CLI only)."
  exit 0
fi

echo
echo "Building GUI (macOS)..."

if ! command -v wails >/dev/null 2>&1; then
  echo "⚠  wails not found — skipping GUI build."
  echo "   Install: go install github.com/wailsapp/wails/v2/cmd/wails@latest"
  echo; echo "Done (CLI only)."
  exit 0
fi

wails build -ldflags "-X main.version=${VERSION}"
echo "GUI app: build/bin/roku-beta-loader-gui.app"

echo
echo "Done."

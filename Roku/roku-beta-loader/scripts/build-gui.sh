#!/usr/bin/env bash
#
# Build the roku-beta-loader GUI using Wails.
#
# Prerequisites (Linux):
#   sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.0-dev
#   or on Ubuntu 24.04+/Pop!_OS 24.04+:
#   sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.1-dev
#
# Prerequisites (all platforms):
#   go install github.com/wailsapp/wails/v2/cmd/wails@latest
#
# Usage:
#   scripts/build-gui.sh               # build for current platform
#   scripts/build-gui.sh --clean       # clean Wails build cache first
#
# The GUI binary is written to build/bin/ by Wails.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v wails >/dev/null 2>&1; then
  echo "Error: wails not found. Install it with:" >&2
  echo "  go install github.com/wailsapp/wails/v2/cmd/wails@latest" >&2
  exit 1
fi

WAILS_TAGS="${WAILS_TAGS:-}"
if [[ -z "$WAILS_TAGS" && "$(uname -s)" == "Linux" ]]; then
  if pkg-config --exists gtk+-3.0 webkit2gtk-4.0; then
    WAILS_TAGS=""
  elif pkg-config --exists gtk+-3.0 webkit2gtk-4.1; then
    WAILS_TAGS="webkit2_41"
  else
    echo "Error: missing Linux GUI build dependencies." >&2
    echo "Install one of these package sets, then rerun this script:" >&2
    echo "  sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.0-dev" >&2
    echo "  sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.1-dev" >&2
    exit 1
  fi
fi

CLEAN=""
if [[ "${1:-}" == "--clean" ]]; then
  CLEAN="-clean"
fi

# Resolve a version string.
if [[ -n "${VERSION:-}" ]]; then
  VERSION="$VERSION"
elif git -C "$PROJECT_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  VERSION="$(git -C "$PROJECT_ROOT" describe --tags --always --dirty 2>/dev/null || echo dev)"
else
  VERSION="dev"
fi

echo "Building roku-beta-loader-gui ${VERSION}"
if [[ -n "$WAILS_TAGS" ]]; then
  wails build ${CLEAN} -tags "$WAILS_TAGS" -ldflags "-X main.version=${VERSION}"
else
  wails build ${CLEAN} -ldflags "-X main.version=${VERSION}"
fi

echo
echo "GUI binary: build/bin/roku-beta-loader-gui"

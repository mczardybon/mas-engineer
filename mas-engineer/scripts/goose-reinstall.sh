#!/usr/bin/env bash
# goose-reinstall.sh — Uninstall current goose, install latest, verify
#
# This is the "fresh goose" gate. Per user rule (2026-07-19):
#   "bei jedem test: aus der installierten goosen deinstallieren und
#    anschliessend die aktuelle Version installiert werden"
#
# Translation: Before every test, uninstall the current goose, then
# install the latest version. This guarantees the test runs against
# the most recent goose, not whatever happens to be cached.
#
# Usage:
#   ./scripts/goose-reinstall.sh
#
# Returns:
#   0 — installed latest version successfully
#   1 — install or download failed
#
# Side effects:
#   - Removes /root/.local/bin/goose
#   - Removes ~/.config/goose (config + recipes + sessions)
#   - Downloads latest release to /root/.local/bin/goose
#   - Verifies `goose --version` works
#
# Note: this does NOT export DEEPSEEK_API_KEY. Caller must do that.

set -e

GOOSE_BIN="/root/.local/bin/goose"
GOOSE_TMP="/tmp/goose-install-$$"
GOOSE_REPO="aaif-goose/goose"
GOOSE_VERSION_URL="https://api.github.com/repos/${GOOSE_REPO}/releases/latest"

echo "=== STEP 1/5: Uninstall current goose ==="
if [ -f "$GOOSE_BIN" ]; then
  echo "Removing $GOOSE_BIN..."
  rm -f "$GOOSE_BIN"
  echo "OK: goose binary removed"
else
  echo "No goose binary found at $GOOSE_BIN (skipped)"
fi

# Clean config (recipes, sessions, settings)
if [ -d "$HOME/.config/goose" ]; then
  echo "Removing $HOME/.config/goose..."
  rm -rf "$HOME/.config/goose"
  echo "OK: goose config removed"
else
  echo "No goose config found (skipped)"
fi

echo ""
echo "=== STEP 2/5: Detect latest version ==="
LATEST_TAG=$(curl -sL "$GOOSE_VERSION_URL" | grep '"tag_name":' | head -1 | sed -E 's/.*"v?([^"]+)".*/\1/')
if [ -z "$LATEST_TAG" ]; then
  echo "FAIL: could not detect latest version from $GOOSE_VERSION_URL"
  exit 1
fi
echo "Latest version: v$LATEST_TAG"

echo ""
echo "=== STEP 3/5: Download latest release ==="
mkdir -p "$GOOSE_TMP"
cd "$GOOSE_TMP"

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
  x86_64) GOOSE_ARCH="x86_64-unknown-linux-gnu" ;;
  aarch64) GOOSE_ARCH="aarch64-unknown-linux-gnu" ;;
  *)
    echo "FAIL: unsupported architecture: $ARCH"
    exit 1
    ;;
esac

DOWNLOAD_URL="https://github.com/${GOOSE_REPO}/releases/download/v${LATEST_TAG}/goose-${GOOSE_ARCH}.tar.bz2"
echo "Downloading $DOWNLOAD_URL..."
if ! curl -sL -o "goose.tar.bz2" "$DOWNLOAD_URL"; then
  echo "FAIL: download failed"
  exit 1
fi

if [ ! -s "goose.tar.bz2" ]; then
  echo "FAIL: downloaded file is empty"
  exit 1
fi
echo "OK: downloaded $(du -h goose.tar.bz2 | cut -f1)"

echo ""
echo "=== STEP 4/5: Extract and install ==="
tar -xjf "goose.tar.bz2"
# The archive contains a directory like goose-X.Y.Z-<arch>/goose
EXTRACTED=$(find . -name "goose" -type f -executable | head -1)
if [ -z "$EXTRACTED" ]; then
  echo "FAIL: goose binary not found in archive"
  exit 1
fi

mkdir -p "/root/.local/bin"
cp "$EXTRACTED" "$GOOSE_BIN"
chmod +x "$GOOSE_BIN"
echo "OK: installed to $GOOSE_BIN"

echo ""
echo "=== STEP 5/5: Verify ==="
export PATH="/root/.local/bin:$PATH"
INSTALLED_VERSION=$("$GOOSE_BIN" --version 2>&1 | head -1)
echo "Installed version: $INSTALLED_VERSION"

# Cleanup
cd /
rm -rf "$GOOSE_TMP"

if echo "$INSTALLED_VERSION" | grep -q "$LATEST_TAG"; then
  echo ""
  echo "============================================="
  echo "GOOSE REINSTALLED: v$LATEST_TAG"
  echo "============================================="
  echo ""
  echo "Next: set DEEPSEEK_API_KEY and run E2E tests:"
  echo "  export DEEPSEEK_API_KEY=sk-..."
  echo "  export PATH=\"/root/.local/bin:\$PATH\""
  echo "  ./scripts/e2e-test.sh"
  exit 0
else
  echo "FAIL: installed version ($INSTALLED_VERSION) does not match latest ($LATEST_TAG)"
  exit 1
fi

#!/usr/bin/env bash
# Prepare the official STOVE Uploader CLI (a Windows-only PyInstaller build) to run on macOS.
# Nothing from Smilegate is committed: this downloads the official package, unpacks its
# Python 3.11 bytecode and installs native macOS dependencies. Safe to run again to update.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CACHE="$ROOT/.cache"
mkdir -p "$CACHE"

CLI_URL="https://dl-sgvn.onstove.com/tools/UploadTool/STOVEUploaderCLI.zip"
XTRACT_URL="https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py"

# 1) Python 3.11, the version the bytecode was compiled with
UV="$(command -v uv || true)"
if [ -z "$UV" ]; then
  python3 -m pip install -q --target "$CACHE/uvpkg" uv
  UV="$CACHE/uvpkg/bin/uv"
fi
export UV_PYTHON_INSTALL_DIR="$CACHE/pythons" UV_CACHE_DIR="$CACHE/uvcache"
"$UV" python install --no-bin 3.11 >/dev/null
PY="$(ls -d "$CACHE"/pythons/cpython-3.11.*/bin/python3.11 | head -1)"
xattr -dr com.apple.quarantine "$CACHE/pythons" 2>/dev/null || true

# 2) Official CLI package + PyInstaller unpacker
echo "Downloading STOVE Uploader CLI..."
curl -fsSL -o "$CACHE/cli.zip" "$CLI_URL"
rm -rf "$CACHE/cli" && mkdir "$CACHE/cli" && unzip -q "$CACHE/cli.zip" -d "$CACHE/cli"
EXE="$(find "$CACHE/cli" -name STOVEUploaderCLI.exe | head -1)"
curl -fsSL -o "$CACHE/pyinstxtractor.py" "$XTRACT_URL"

# 3) Native macOS dependencies, pinned to the versions bundled in the Windows exe
echo "Installing Python dependencies..."
rm -rf "$ROOT/deps"
PIP_REQUIRE_VIRTUALENV=false "$PY" -m pip install -q --disable-pip-version-check --target "$ROOT/deps" \
  -r "$ROOT/requirements-mac.txt"
xattr -dr com.apple.quarantine "$ROOT/deps" 2>/dev/null || true

# 4) CLI runner. The Updater and Core are downloaded by the CLI and unpacked on first use.
read -r ENTRY VERSION < <(STOVE_MAC_ROOT="$ROOT" "$PY" -I "$ROOT/patches/stove_mac.py" extract "$EXE" "$ROOT/runner")
echo "Ready: STOVE Uploader CLI v$VERSION ($ENTRY)."
echo "Try:   $ROOT/stove-uploader --help"

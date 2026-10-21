#!/usr/bin/env bash
# Upload a Windows game build folder to STOVE from this Mac.
#   ./upload.sh <build-dir> ["description"] [extra uploader options...]
# Settings come from stove.local.env next to this script (gitignored):
#   STOVE_GAME_ID=GM-XXXX-XXXXXXXX_IND   STOVE_USER=you@example.com   [STOVE_CALLER_DETAIL=<key>, optional]
# The password is read from the macOS Keychain (service "stove-uploader"); store it once with
#   security add-generic-password -s stove-uploader -a you@example.com -w
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
[ -f "$ROOT/stove.local.env" ] && source "$ROOT/stove.local.env"
: "${STOVE_GAME_ID:?Set STOVE_GAME_ID in $ROOT/stove.local.env}"
: "${STOVE_USER:?Set STOVE_USER in $ROOT/stove.local.env}"
case "$STOVE_GAME_ID" in
  GM-*) ;;
  *) echo "Warning: STOVE_GAME_ID usually looks like GM-XXXX-XXXXXXXX_IND, not a product number." >&2;;
esac

[ $# -ge 1 ] || { echo "Usage: $0 <build-dir> [\"description\"] [extra options]" >&2; exit 1; }
SRC="$(cd "$1" && pwd)"; shift
DESC="${1:-$(basename "$SRC") $(date +%Y-%m-%d)}"; [ $# -ge 1 ] && shift
[ ${#DESC} -le 60 ] || { echo "Description must be 60 characters or fewer." >&2; exit 1; }

if ! PW="$(security find-generic-password -s stove-uploader -a "$STOVE_USER" -w 2>/dev/null)"; then
  read -r -s -p "STOVE password for $STOVE_USER: " PW; echo
fi

[ -f "$ROOT/runner/.runner" ] || "$ROOT/setup.sh"
EXTRA=()
[ -n "${STOVE_CALLER_DETAIL:-}" ] && EXTRA=(-cd "$STOVE_CALLER_DETAIL")
# Unity writes a Burst debug folder next to the player; it must not ship.
SKIP=".DS_Store"
for d in "$SRC"/*_BurstDebugInformation_DoNotShip; do [ -d "$d" ] && EXTRA+=(-ed "$(basename "$d")"); done
echo "Uploading $SRC to $STOVE_GAME_ID as \"$DESC\""
exec "$ROOT/stove-uploader" -g "$STOVE_GAME_ID" -s "$SRC" -d "$DESC" -id "$STOVE_USER" -pw "$PW" \
  -ef "$SKIP" ${EXTRA[@]+"${EXTRA[@]}"} "$@"

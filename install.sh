#!/usr/bin/env bash
# One-command installer for AI Usage Dashboard on macOS.
set -euo pipefail

REPO="XinyuIvy/ai-usage-check"
CCLIMITS_REF="922ddac93894139da24ba6cf25de1f2f39f96543"
APP_DIR="${AI_USAGE_HOME:-$HOME/.local/share/ai-usage-check}"
BIN_DIR="$HOME/.local/bin"
PLIST_DIR="$HOME/Library/LaunchAgents"
SERVICE_PLIST="$PLIST_DIR/com.aiusage.dashboard.plist"
UPDATE_PLIST="$PLIST_DIR/com.aiusage.update.plist"
PORT="${AI_USAGE_PORT:-8899}"
SOURCE_DIR=""
SOURCE_WAS_EXPLICIT=0

if [ "${1:-}" = "--source" ]; then
  SOURCE_DIR="${2:?--source requires a directory}"
  SOURCE_WAS_EXPLICIT=1
elif [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
else
  # A script received through stdin has no reliable adjacent project directory.
  SOURCE_DIR=""
fi

has_complete_source() {
  [ -n "${1:-}" ] && \
    [ -f "$1/server.py" ] && \
    [ -f "$1/bin/ai-usage-check" ] && \
    [ -f "$1/scripts/install_widget.sh" ] && \
    [ -f "$1/uninstall.sh" ]
}

# A piped installer has no adjacent files, so always fetch a clean release copy.
if ! has_complete_source "$SOURCE_DIR"; then
  if [ "$SOURCE_WAS_EXPLICIT" = "1" ]; then
    echo "The installation source is incomplete: $SOURCE_DIR"
    echo "Expected server.py, bin/ai-usage-check, scripts/install_widget.sh, and uninstall.sh."
    exit 1
  fi
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' EXIT
  echo "Downloading AI Usage Dashboard ..."
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$temp_dir"
  exec bash "$temp_dir/ai-usage-check-main/install.sh" --source "$temp_dir/ai-usage-check-main"
fi

if [ "$(uname -s)" != "Darwin" ]; then
  echo "The automated installer currently supports macOS only."
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it, then run this command again."
  exit 1
fi

echo "Installing to $APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR" "$PLIST_DIR"
if [ "$SOURCE_DIR" != "$APP_DIR" ]; then
  tar -C "$SOURCE_DIR" --exclude=.git --exclude=cclimits.py -cf - . | tar -C "$APP_DIR" -xf -
fi

if ! has_complete_source "$APP_DIR"; then
  echo "Installation failed because required application files are missing from $APP_DIR."
  exit 1
fi

# Keep the collector local. Existing copies are preserved during normal reinstalls.
if [ ! -f "$APP_DIR/cclimits.py" ]; then
  echo "Downloading quota collector ..."
  curl -fsSL -o "$APP_DIR/cclimits.py" \
    "https://raw.githubusercontent.com/cruzanstx/cclimits/$CCLIMITS_REF/lib/cclimits.py"
fi

python_bin="$(command -v python3)"
cat > "$SERVICE_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.aiusage.dashboard</string>
  <key>ProgramArguments</key><array><string>$python_bin</string><string>$APP_DIR/server.py</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/ai-usage-dashboard.log</string>
  <key>StandardErrorPath</key><string>/tmp/ai-usage-dashboard.err</string>
</dict></plist>
PLIST

chmod +x "$APP_DIR/bin/ai-usage-check" "$APP_DIR/scripts/install_widget.sh" "$APP_DIR/uninstall.sh"
ln -sfn "$APP_DIR/bin/ai-usage-check" "$BIN_DIR/ai-usage-check"

cat > "$UPDATE_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.aiusage.update</string>
  <key>ProgramArguments</key><array><string>$BIN_DIR/ai-usage-check</string><string>update</string></array>
  <key>StartInterval</key><integer>86400</integer>
  <key>StandardOutPath</key><string>/tmp/ai-usage-update.log</string>
  <key>StandardErrorPath</key><string>/tmp/ai-usage-update.err</string>
</dict></plist>
PLIST

launchctl unload "$SERVICE_PLIST" 2>/dev/null || true
launchctl load "$SERVICE_PLIST"
if [ "${AI_USAGE_UPDATING:-0}" != "1" ]; then
  launchctl unload "$UPDATE_PLIST" 2>/dev/null || true
  launchctl load "$UPDATE_PLIST"
fi

sleep 2
phone_url=""
if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
  serve_output="$(tailscale serve --bg "$PORT" 2>&1 || true)"
  phone_url="$(tailscale status --json 2>/dev/null | python3 -c '
import json,sys
try:
 name=json.load(sys.stdin).get("Self", {}).get("DNSName", "").rstrip(".")
 print("https://" + name if name else "")
except Exception: print("")
' || true)"
fi

echo ""
echo "Installed. Local dashboard: http://127.0.0.1:$PORT"
if [ -n "$phone_url" ]; then
  echo "Private phone URL: $phone_url"
  "$APP_DIR/scripts/install_widget.sh" || true
else
  echo "For automatic phone setup, install and sign in to Tailscale, then run:"
  echo "  $BIN_DIR/ai-usage-check restart"
  echo "  $BIN_DIR/ai-usage-check widget"
fi
echo ""
echo "Run diagnostics: $BIN_DIR/ai-usage-check doctor"
echo "If the command is not found, add $BIN_DIR to PATH or use the full path above."

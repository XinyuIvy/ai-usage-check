#!/usr/bin/env bash
# Install the stable Scriptable loader and its server configuration through iCloud.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTABLE_DIR="$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents"

if [ ! -d "$SCRIPTABLE_DIR" ]; then
  echo "Open Scriptable once on your iPhone with iCloud enabled, then run: ai-usage-check widget"
  open "https://apps.apple.com/app/scriptable/id1405459188" 2>/dev/null || true
  exit 1
fi

url=""
if command -v tailscale >/dev/null 2>&1; then
  url="$(tailscale status --json 2>/dev/null | python3 -c '
import json,sys
try:
 name=json.load(sys.stdin).get("Self", {}).get("DNSName", "").rstrip(".")
 print("https://" + name if name else "")
except Exception: print("")
')"
fi

if [ -z "$url" ]; then
  echo "Tailscale Serve is not ready. Run: tailscale serve --bg 8899"
  exit 1
fi

cp "$APP_DIR/scripts/scriptable_loader.js" "$SCRIPTABLE_DIR/AI Usage.js"
printf '{"server_url":"%s"}\n' "$url" > "$SCRIPTABLE_DIR/ai_usage_config.json"
echo "Widget script installed through iCloud: AI Usage"
echo "On iPhone, add one Scriptable widget and select AI Usage. Future code updates are automatic."

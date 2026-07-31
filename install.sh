#!/usr/bin/env bash
# Installs the AI Usage Dashboard as a background service (macOS launchd).
# Run this from inside the repo folder: ./install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_DST="$HOME/Library/LaunchAgents/com.aiusage.dashboard.plist"

echo "Repo directory: $REPO_DIR"

# 1. Fetch cclimits if it's not already vendored
if [ ! -f "$REPO_DIR/cclimits.py" ]; then
  echo "Downloading cclimits.py ..."
  curl -fsSL -o "$REPO_DIR/cclimits.py" \
    https://raw.githubusercontent.com/cruzanstx/cclimits/main/lib/cclimits.py
fi

# 2. Render the LaunchAgent plist with the real install path
#    (macOS background services can't reliably read Documents/Desktop,
#    so this repo should NOT live under ~/Documents or ~/Desktop.)
mkdir -p "$(dirname "$PLIST_DST")"
sed "s|__INSTALL_DIR__|$REPO_DIR|g" \
  "$REPO_DIR/com.aiusage.dashboard.plist.template" > "$PLIST_DST"

# 3. (Re)load the service
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

sleep 1
echo ""
echo "Installed and started."
echo "  On this Mac:   http://127.0.0.1:8899"
echo "  On your phone: http://$(ipconfig getifaddr en0 2>/dev/null || echo '<your-computer-ip>'):8899   (same Wi-Fi)"
if command -v tailscale >/dev/null 2>&1; then
  TAILSCALE_IP="$(tailscale ip -4 2>/dev/null | head -n 1 || true)"
  if [ -n "$TAILSCALE_IP" ]; then
    echo "  Stable phone URL: http://$TAILSCALE_IP:8899   (Tailscale; works across Wi-Fi/cellular)"
  else
    echo "  Tailscale is installed but not connected. Open Tailscale and sign in once."
  fi
else
  echo "  For a stable phone URL across networks, install Tailscale on this Mac and your iPhone."
fi
echo ""
echo "Logs: /tmp/ai-usage-dashboard.log and /tmp/ai-usage-dashboard.err"
echo "To uninstall: launchctl unload $PLIST_DST && rm $PLIST_DST"

#!/usr/bin/env bash
# Remove the background service and command; keep user credentials untouched.
set -euo pipefail

APP_DIR="${AI_USAGE_HOME:-$HOME/.local/share/ai-usage-check}"
PLIST="$HOME/Library/LaunchAgents/com.aiusage.dashboard.plist"
launchctl unload "$PLIST" 2>/dev/null || true
[ ! -f "$PLIST" ] || rm "$PLIST"
[ ! -L "$HOME/.local/bin/ai-usage-check" ] || rm "$HOME/.local/bin/ai-usage-check"
echo "Service removed. App files remain at $APP_DIR and can be deleted if no longer needed."


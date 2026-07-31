# AI Usage Dashboard

See your **Claude**, **Codex/ChatGPT**, and **Gemini (Antigravity CLI)** quota — 5-hour and weekly windows — in one place: a phone widget, a menu bar item, a desktop card, or a plain web page.

It works by reading the login credentials already saved on your computer by the `claude`, `codex`, and `agy` (Antigravity) CLIs, and querying each provider's (undocumented) usage API through the open-source [cclimits](https://github.com/cruzanstx/cclimits) tool. A small local server then serves that data to a phone-friendly web page, and a set of ready-made widgets render it.

> **Privacy note:** everything runs locally on your machine. No credentials or usage data are sent anywhere except the official Claude / OpenAI / Google endpoints used to check your own quota.

## What you get

- 📱 A **phone widget** (iOS, via [Scriptable](https://scriptable.app)) — medium (compact) and large (detailed, with reset times) layouts
- 🖥️ A **menu bar item** (macOS, via [SwiftBar](https://github.com/swiftbar/SwiftBar))
- 🖼️ A **desktop card** (macOS, via [Übersicht](https://tracesof.net/uebersicht/))
- 🌐 A plain **web dashboard**, installable as a home-screen "app" (PWA) on any phone

All four read from the same local server, so they always agree.

## Requirements

- macOS (the Keychain-reading code for Antigravity credentials is macOS-only; everything else is cross-platform)
- Python 3.9+
- At least one of `claude`, `codex`, or `agy` (Antigravity) CLI installed and logged in — cards for providers you haven't logged into will just show "No credentials found"

## Quick start

```bash
git clone https://github.com/XinyuIvy/ai-usage-check.git
cd ai-usage-check
bash install.sh
```

This will:
1. Download `cclimits.py` next to `server.py` if it's not already there
2. Register the dashboard as a background service (auto-starts on login, restarts if it crashes)
3. Print the local and phone-accessible URLs

Open the printed `http://127.0.0.1:8899` URL to confirm it's running.

> ⚠️ **Don't put this repo inside `~/Documents` or `~/Desktop`.** macOS blocks background (launchd) processes from reading those folders even with the LaunchAgent installed correctly. Anywhere else in your home folder (e.g. `~/ai-usage-dashboard`) is fine.

### Not logged into a provider yet?

```bash
claude          # Claude Code — opens a browser to log in, then Ctrl+C to quit
codex login     # Codex / ChatGPT
agy             # Antigravity (Gemini) — choose "Google OAuth"
```

Cards refresh automatically; no need to restart the server after logging in.

## Setting up each widget

### Phone widget (iOS + Scriptable)

1. Install **Scriptable** from the App Store
2. Create a new script, paste in `scripts/scriptable_widget.js`
3. Run the script once inside Scriptable and enter the stable Tailscale URL printed by `install.sh`
4. Long-press your home screen → add widget → Scriptable → Medium or Large → pick your script

The URL is saved in the iPhone Keychain and reused automatically. Tapping the widget opens the full dashboard. You do not need to scan a QR code again or edit the script after changing Wi-Fi.

### Menu bar (macOS + SwiftBar)

1. Install [SwiftBar](https://github.com/swiftbar/SwiftBar)
2. Point it at a plugin folder, then copy `scripts/swiftbar_plugin.py` in
3. `chmod +x` the file (the `.5m` in the filename sets a 5-minute refresh)

### Desktop card (macOS + Übersicht)

1. Install [Übersicht](https://tracesof.net/uebersicht/)
2. Open its widgets folder and copy `scripts/ubersicht_widget.jsx` in
3. Adjust `top` / `right` (or `bottom` / `left`) in the file's `className` to place it wherever you like

### Web page / PWA

Just open `http://127.0.0.1:8899` (or your phone-accessible address) in a browser. On iOS Safari, use *Share → Add to Home Screen* for an app-like icon with no browser chrome.

## Viewing it away from home

Since the server only runs on your machine, your phone needs to reach that machine's IP — which normally means "same Wi-Fi." Two ways around that:

- **[Tailscale](https://tailscale.com)** (recommended, free): install it on the computer and phone and log in with the same account once. The computer gets a stable `100.x.x.x` address that works across home Wi-Fi, other Wi-Fi networks, and cellular data (as long as the computer is on). `install.sh` detects and prints this stable URL; enter it once when Scriptable first runs. No repeated QR scan or IP update is needed.
- **DHCP reservation**: if you only ever move between a couple of known Wi-Fi networks, give your computer a fixed IP on each router instead.

## How the data flows

```
claude / codex / agy CLI  ->  saves login credentials locally
                              (files, or macOS Keychain for agy)
                |
         cclimits.py       ->  reads those credentials, calls each
                              provider's usage API
                |
          server.py        ->  runs cclimits every ~5 min, caches
                              results, serves JSON + a web page
                |
   phone / menu bar / desktop widgets  ->  poll server.py and render
```

## Troubleshooting

- **A card shows "No credentials found"** — you haven't logged into that CLI on this machine yet (see above)
- **A card shows "Token expired"** — re-run the login command for that provider
- **Occasional `HTTP 429` briefly, then it clears itself** — the usage API is rate-limited; the server caches the last successful result and serves that instead of an error once it has one
- **Background service fails silently after install** — check `/tmp/ai-usage-dashboard.err`. The most common cause is the repo living under `~/Documents` (see the warning above) or launchd invoking an old system Python — the `install.sh` script and `server.py` are written to be safe against both, but if you edit `server.py` keep the `from __future__ import annotations` line at the top

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.aiusage.dashboard.plist
rm ~/Library/LaunchAgents/com.aiusage.dashboard.plist
```

Then just delete the repo folder.

## Credits

Built on top of [cclimits](https://github.com/cruzanstx/cclimits) for the actual provider API calls.

## License

MIT — do whatever you want with it.

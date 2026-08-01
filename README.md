# AI Usage Dashboard

[中文说明](README.zh-CN.md)

See remaining **Claude Code**, **Codex on ChatGPT**, and **Google Antigravity CLI** quota in one iPhone widget and a Mac web dashboard.

The project reads credentials already stored by the official CLIs. Credentials stay on the Mac. The phone receives only quota results and keeps the last successful snapshot for display while the Mac is off.

## Preview

| Detailed view | Compact widget |
| --- | --- |
| <img src="docs/images/detailed-widget.jpeg" alt="Detailed AI usage view" width="360"> | <img src="docs/images/compact-widget.jpeg" alt="Compact AI usage widget" width="520"> |

## How it works

The Mac collects quota data from the AI command-line tools you already use and serves the result only on `127.0.0.1`. Tailscale Serve provides a private HTTPS address for your iPhone. Scriptable renders that data as a widget and saves the last successful result in iCloud, so it can show a clearly labeled cached snapshot while the Mac is off.

No provider password, OAuth token, or CLI credential is copied to the phone or uploaded by this project.

## First-time setup

Before installing, complete these one-time requirements:

1. Use macOS with Python 3 available.
2. Install and sign in to at least one supported CLI: Claude Code, Codex, or Google Antigravity.
3. Install Tailscale on the Mac and iPhone, sign in to the same tailnet, and confirm both devices show as connected.
4. Install Scriptable on the iPhone. Enable Scriptable under iPhone **Settings → Apple Account → iCloud → See All**, then open Scriptable once so its iCloud folder is created.

## Install

On a Mac, run:

```bash
curl -fsSL https://raw.githubusercontent.com/XinyuIvy/ai-usage-check/main/install.sh | bash
```

The installer downloads the app to `~/.local/share/ai-usage-check`, starts it at login, enables daily app updates, configures a private Tailscale HTTPS address when available, and installs the iPhone widget through iCloud when Scriptable has been opened once.

Then run the automatic check:

```bash
~/.local/bin/ai-usage-check doctor
```

The installer should finish in under a minute on a normal connection. If Tailscale does not respond, it stops waiting after eight seconds and finishes the local setup.

Apple does not allow software to add a home-screen widget automatically. Complete this final one-time step on the iPhone:

1. Long-press the Home Screen and tap **+**.
2. Add a Scriptable widget; medium size is recommended.
3. Long-press the new widget, choose **Edit Widget**, and select **AI Usage** as the script.

Everything after that is automatic.

If Scriptable was not ready during installation, open it once and run:

```bash
~/.local/bin/ai-usage-check widget
```

## Automatic behavior

- The Mac service starts at login and restarts after a crash.
- The Mac app checks for updates daily.
- The Scriptable loader checks for widget updates daily and retains a working backup.
- Network changes do not change the private Tailscale URL.
- When the Mac is off, the widget shows its last snapshot as `cached` with its age.
- When the Mac returns, the widget switches back to live data.

## Troubleshooting

Run the diagnostic command first:

```bash
~/.local/bin/ai-usage-check doctor
```

- `HTTP 429` for one provider means that provider temporarily rate-limited quota collection. The other providers still work; retry later.
- If installation reports that Tailscale did not respond, open the Tailscale app, reconnect it, then run `~/.local/bin/ai-usage-check widget`.
- If the local dashboard works but the phone does not, confirm Tailscale is connected on both devices and select `AI Usage` in the Scriptable widget settings.
- If Scriptable has no `AI Usage` script, confirm iCloud is enabled for Scriptable, open the app once, then run the widget command again.
- View service errors with `~/.local/bin/ai-usage-check logs`.

## Commands

```bash
ai-usage-check status
ai-usage-check doctor
ai-usage-check open
ai-usage-check restart
ai-usage-check update
ai-usage-check widget
ai-usage-check logs
ai-usage-check uninstall
```

If `ai-usage-check` is not on your shell path, use `~/.local/bin/ai-usage-check`.

## What cannot be automated

- Logging into Claude, Codex, Google, Tailscale, or iCloud
- Installing an iPhone home-screen widget
- Refresh timing: iOS decides when widgets refresh, so updates are near-real-time rather than continuous
- Live collection while the Mac is off; only the last snapshot remains available

## Privacy and stability

This project relies on undocumented quota endpoints through [cclimits](https://github.com/cruzanstx/cclimits), so providers can change behavior without notice. Do not expose the server to the public internet. Use private Tailscale Serve, never Tailscale Funnel or router port forwarding.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Automated syntax checks run on every pull request.

## License

MIT

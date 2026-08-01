# AI Usage Dashboard

See remaining **Claude Code**, **Codex on ChatGPT**, and **Google Antigravity CLI** quota in one iPhone widget and a Mac web dashboard.

The project reads credentials already stored by the official CLIs. Credentials stay on the Mac. The phone receives only quota results and keeps the last successful snapshot for display while the Mac is off.

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

## First-time requirements

- macOS and Python 3
- At least one logged-in CLI: `claude`, `codex`, or `agy`
- Tailscale on the Mac and iPhone, signed into the same tailnet
- Scriptable on the iPhone with iCloud enabled

Apple does not allow software to add a home-screen widget automatically. On the iPhone, long-press the home screen, add a Scriptable widget, and select **AI Usage** once. Everything after that is automatic.

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

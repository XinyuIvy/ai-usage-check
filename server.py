#!/usr/bin/env python3
"""
AI Usage Dashboard — check remaining Claude / Codex (ChatGPT) / Gemini
(Antigravity) quota from your phone, menu bar, or desktop.

How it works:
  Runs on a computer where you're already logged into the claude / codex /
  agy (Antigravity) CLIs. Uses the open-source cclimits tool to read each
  CLI's local credentials and query each provider's (undocumented) usage
  API, then serves a phone-friendly web page on your LAN (default port
  8899).

Usage:
  1) Make sure cclimits.py sits next to this file (see install.sh / README),
     or that Node.js is installed so `npx cclimits` works. Python 3.9+ is
     the only hard requirement otherwise.
  2) python3 server.py
  3) On your phone, same Wi-Fi, open http://<this-computer's-IP>:8899
     (this script prints the address on startup). For access away from
     home, pair this with Tailscale — see the README.

Security note: the page is read-only and never exposes your tokens, but
it's still meant for a trusted LAN / Tailscale network, not the public
internet.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8899
CACHE_TTL = 300  # seconds; manual Refresh on the page forces a fresh query
PROVIDERS_ARGS = ["--claude", "--codex", "--antigravity"]

# 180x180 PNG icon (base64), used for "Add to Home Screen" on iOS/Android
ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAACeElEQVR42u3dMS4EYRTAcTsZSpVCQkGtEBfYC2h0GmdQ6FV6hTNodBoXcAFRbK0hcQYkVNqVkWHee9/v10rsrO/v5cXIzmx9Y+dzBYro/AgQNAgaBA2CRtAgaBA0CBoEjaBB0CBoEDQIGkGDoEHQIGgQNIIGQYOgQdAgaAQNggZBg6BB0AgaBA2CBkGDoKmmz3Kh+/cXTquox/n5aN9rFv2hQUIWdpmVQ8xtGeO8OzFT6dw7MVPp/P2Vg1K6Sr+dmNImNCY0CBoEDcmDHvM2KHn9tgMTGhPalCbq+XcV3xRtxhx+5RC1mIcK/++j39xBFHKpoCH9ygGCRtAgaBA0CBoEjaBB0CBoEDQIGkGDoEHQIGgQNIIGQYOgQdAgaAQNggZBg6BB0AgaUuizXOjz9Z7T+mObxw/LY1ldC/8ewn/6qJCFXWblEPM0Xm8Oln794/1N0GIWdbNBi1nUJVcOSB+06WxKm9AgaAQNgoaGg94+WTiVQLLdNTShMaFNadM54nQOPaFFLeZyK4eoxTxUmofXu4Mo5FJBQ/qVAwSNoEHQIGgQNAgaQYOgQdAgaBA0ggZBg6BB0CBoBA2CBkGDoEHQCBoEDYIGQYOgETSk0Ge50Mvbp+YP6/Rwa9pYfPqokIVt5RDzD67uXiZ9/agPrg8dtJhFXSZoMYu65MoB6YM2nU1pExoEjaBB0NBw0GdHu05lAHcNTWhMaFPadI4/nUNPaFGLudzKIWoxD5Xm4fXuIAq5VNCQfuUAQSNoEDQIGgQNgkbQIGgQNAgaBI2gQdAgaBA0CBpBg6BB0CBoEDSCBkGDoEHQIGgEDYIGQYOgQdAIGgQN/+YLc+uI74vGkGYAAAAASUVORK5CYII="

_cache = {"ts": 0.0, "data": None}
_last_good: dict = {}
_lock = threading.Lock()


def find_collector() -> list[str] | None:
    """Find a runnable cclimits command, in order of preference."""
    if shutil.which("cclimits"):
        return ["cclimits"]
    local = Path(__file__).parent / "cclimits.py"
    if local.exists():
        return ["python3", str(local)]
    if shutil.which("npx"):
        return ["npx", "-y", "cclimits"]
    return None



def _collector_env() -> dict:
    """macOS: Antigravity CLI (agy) stores its OAuth token in the Keychain
    (service 'gemini', account 'antigravity'), wrapped by go-keyring, instead
    of a file cclimits can read directly. Unwrap it and hand it over via env
    vars so cclimits can use it. No-op on other platforms / if already set."""
    env = os.environ.copy()
    if sys.platform != "darwin" or env.get("ANTIGRAVITY_REFRESH_TOKEN"):
        return env
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "gemini",
             "-a", "antigravity", "-w"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if not out:
            return env
        # go-keyring wraps payloads as "go-keyring-base64:<base64>"
        if out.startswith("go-keyring") and ":" in out:
            import base64
            b64 = out.split(":", 1)[1]
            b64 += "=" * (-len(b64) % 4)
            out = base64.b64decode(b64).decode("utf-8", errors="replace")
        refresh = access = None
        try:
            data = json.loads(out)
            tok = data.get("token", data) if isinstance(data, dict) else {}
            refresh = tok.get("refresh_token")
            access = tok.get("access_token")
        except Exception:
            refresh = out
        if refresh:
            env["ANTIGRAVITY_REFRESH_TOKEN"] = refresh
        if access:
            env["ANTIGRAVITY_ACCESS_TOKEN"] = access
    except Exception:
        pass
    return env


def collect(force: bool = False) -> dict:
    with _lock:
        now = time.time()
        ttl = 30 if force else CACHE_TTL
        if _cache["data"] is not None and now - _cache["ts"] < ttl:
            return _cache["data"]

        cmd = find_collector()
        if cmd is None:
            return {
                "_error": "cclimits not found. Download it next to this script with: "
                          "curl -O https://raw.githubusercontent.com/cruzanstx/cclimits/main/lib/cclimits.py "
                          "(or install Node.js and run: npm install -g cclimits)"
            }
        try:
            proc = subprocess.run(
                cmd + PROVIDERS_ARGS + ["--json"],
                capture_output=True, text=True, timeout=90,
                env=_collector_env(),
            )
            raw = proc.stdout.strip()
            # npx may mix install logs into first run; take from the first '{'
            idx = raw.find("{")
            data = json.loads(raw[idx:]) if idx >= 0 else {}
            # Per-provider fallback: if a provider errored (e.g. HTTP 429),
            # keep showing the last successful result instead, marked stale.
            for key in ("claude", "codex", "antigravity", "gemini"):
                res = data.get(key)
                if isinstance(res, dict) and "error" not in res:
                    _last_good[key] = (dict(res), now)
                elif key in _last_good:
                    good, ts = _last_good[key]
                    stale = dict(good)
                    stale["stale"] = True
                    stale["stale_minutes"] = int((now - ts) // 60)
                    data[key] = stale
            data["_collected_at"] = now
            _cache["data"], _cache["ts"] = data, now
            return data
        except subprocess.TimeoutExpired:
            return {"_error": "Query timed out (90s), try again later"}
        except Exception as e:  # noqa: BLE001
            return {"_error": f"Collection failed: {e}"}


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0e1420">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="AI Usage">
<title>AI Usage</title>
<style>
  :root{
    --bg:#0e1420; --card:#161e2e; --line:#26314a;
    --text:#e8ecf2; --muted:#7e8aa0;
    --ok:#3dd6a3; --warn:#f2b84b; --bad:#f06a5d;
  }
  *{box-sizing:border-box; margin:0; padding:0}
  body{
    background:var(--bg); color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",Roboto,sans-serif;
    padding:max(16px,env(safe-area-inset-top)) 16px 32px;
    max-width:560px; margin:0 auto;
  }
  header{display:flex; align-items:baseline; justify-content:space-between; margin:8px 2px 18px}
  h1{font-size:19px; font-weight:650; letter-spacing:.5px}
  #meta{font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums}
  .card{
    background:var(--card); border:1px solid var(--line); border-radius:16px;
    padding:16px 16px 14px; margin-bottom:14px;
  }
  .chead{display:flex; align-items:center; gap:10px; margin-bottom:12px}
  .logo{
    width:30px;height:30px;border-radius:9px;display:grid;place-items:center;
    font-size:13px;font-weight:700;color:#0e1420;flex:none;
  }
  .cname{font-size:15px;font-weight:600}
  .csub{font-size:11.5px;color:var(--muted);margin-top:1px}
  .row{margin:11px 0 2px}
  .rowtop{display:flex;justify-content:space-between;align-items:baseline;font-size:13px}
  .rlabel{color:var(--muted)}
  .rpct{font-weight:650;font-variant-numeric:tabular-nums}
  .bar{height:7px;border-radius:4px;background:#0a0f1a;margin-top:6px;overflow:hidden}
  .fill{height:100%;border-radius:4px;transition:width .5s ease}
  .reset{font-size:11.5px;color:var(--muted);margin-top:4px;font-variant-numeric:tabular-nums}
  .err{font-size:13px;color:var(--warn);line-height:1.5}
  .hint{font-size:12px;color:var(--muted);margin-top:4px}
  button{
    background:transparent;border:1px solid var(--line);color:var(--text);
    border-radius:10px;padding:6px 14px;font-size:13px;
  }
  button:active{background:var(--line)}
  footer{font-size:11px;color:var(--muted);line-height:1.6;margin-top:22px;text-align:center}
</style>
</head>
<body>
<header>
  <h1>AI Usage</h1>
  <div style="display:flex;gap:10px;align-items:center">
    <span id="meta">Loading…</span>
    <button onclick="load(true)">Refresh</button>
  </div>
</header>
<div id="cards"></div>
<footer>Remaining = 100% − used. Data comes from each CLI's (undocumented) usage API. Auto-refreshes every 5 min; tap Refresh for live numbers.</footer>

<script>
const BRANDS = {
  claude:{name:"Claude", sub:"Shared quota: Claude Code + claude.ai", color:"#d97757", mark:"C"},
  codex:{name:"Codex / ChatGPT", sub:"Codex quota on your ChatGPT plan", color:"#9cc4ff", mark:"G"},
  gemini:{name:"Gemini (Antigravity)", sub:"Per-model quota, agy CLI", color:"#7ee0c0", mark:"✦"},
};
function pct(s){ const n=parseFloat(String(s||"").replace("%","")); return isNaN(n)?null:n; }
function fmtReset(s){
  if(!s) return null;
  const d=/(\d+)\s*d/.exec(s), h=/(\d+)\s*h/.exec(s), m=/(\d+)\s*m/.exec(s);
  if(!d&&!h&&!m) return null;
  const mins=(d?+d[1]*1440:0)+(h?+h[1]*60:0)+(m?+m[1]:0);
  if(mins>=1440) return Math.floor(mins/1440)+"d "+Math.floor((mins%1440)/60)+"h";
  if(mins>=60) return Math.floor(mins/60)+"h "+(mins%60)+"m";
  return mins+"m";
}
function color(remain){ return remain>40?"var(--ok)":(remain>15?"var(--warn)":"var(--bad)"); }
function bar(label, remainStr, resetStr){
  const r = pct(remainStr);
  const w = r==null?0:Math.max(1.5,Math.min(100,r));
  return `<div class="row">
    <div class="rowtop"><span class="rlabel">${label}</span>
      <span class="rpct" style="color:${color(r??0)}">${r==null?"—":r.toFixed(1)+"%"} left</span></div>
    <div class="bar"><div class="fill" style="width:${w}%;background:${color(r??0)}"></div></div>
    ${resetStr?`<div class="reset">resets in ${fmtReset(resetStr)}</div>`:""}
  </div>`;
}
function card(key, body){
  const b = BRANDS[key];
  return `<div class="card">
    <div class="chead">
      <div class="logo" style="background:${b.color}">${b.mark}</div>
      <div><div class="cname">${b.name}</div><div class="csub">${b.sub}</div></div>
    </div>${body}</div>`;
}
function renderClaude(d){
  if(d.error) return errBody(d);
  let h=staleNote(d);
  if(d.five_hour) h+=bar("5h", d.five_hour.remaining, d.five_hour.resets_in);
  if(d.seven_day) h+=bar("Weekly", d.seven_day.remaining, d.seven_day.resets_in);
  if(d.opus){ const u=pct(d.opus.used); h+=bar("Opus (weekly)", (u==null?null:(100-u).toFixed(1)+"%"), null); }
  return h||'<div class="err">Connected, but no quota data returned</div>';
}
function renderCodex(d){
  if(d.error) return errBody(d);
  let h=staleNote(d);
  if(d.plan) h+=`<div class="hint" style="margin:-4px 0 2px">Plan: ${d.plan}</div>`;
  for(const win of [d.primary_window, d.secondary_window]){
    if(!win) continue;
    const s=String(win.resets_in||"");
    const dd=/(\d+)\s*d/.exec(s), hh=/(\d+)\s*h/.exec(s), mm=/(\d+)\s*m/.exec(s);
    const mins=(dd?+dd[1]*1440:0)+(hh?+hh[1]*60:0)+(mm?+mm[1]:0);
    const label = (mins>320 || /d/.test(String(win.window||""))) ? "Weekly" : "5h";
    h+=bar(label, win.remaining, win.resets_in);
  }
  if(d.limit_reached) h+=`<div class="err">Limit reached</div>`;
  if(d.token_status==="expired") h+=`<div class="err">Login expired — run codex login on your computer</div>`;
  return h||'<div class="err">Connected, but no quota data returned</div>';
}
function renderGemini(d){
  if(d.error) return errBody(d);
  let h=staleNote(d);
  if(d.subscription_tier) h+=`<div class="hint" style="margin:-4px 0 2px">Tier: ${d.subscription_tier}</div>`;
  if(Array.isArray(d.models)){
    for(const m of d.models.slice(0,6)){
      let reset=null;
      if(m.reset_time){ const t=new Date(m.reset_time); if(!isNaN(t)){
        const mins=Math.max(0,Math.round((t-Date.now())/60000));
        reset = mins>=1440 ? Math.floor(mins/1440)+"d "+Math.floor((mins%1440)/60)+"h"
              : mins>=60 ? Math.floor(mins/60)+"h "+(mins%60)+"m" : mins+"m";
      }}
      h+=bar(m.name, m.remaining_pct+"%", reset);
    }
  }
  return h||'<div class="err">Connected, but no quota data returned</div>';
}
function staleNote(d){
  return d.stale ? `<div class="hint" style="margin:-2px 0 4px">showing cached data from ${d.stale_minutes||0} min ago (live query failed, will retry)</div>` : "";
}
function errBody(d){
  return `<div class="err">${d.error}</div>${d.hint?`<div class="hint">${d.hint}</div>`:""}`;
}
async function load(force){
  document.getElementById("meta").textContent = "Refreshing…";
  try{
    const res = await fetch("/api/usage"+(force?"?refresh=1":""));
    const data = await res.json();
    const el = document.getElementById("cards");
    if(data._error){ el.innerHTML = `<div class="card"><div class="err">${data._error}</div></div>`; }
    else{
      el.innerHTML =
        card("claude", renderClaude(data.claude||{error:"No data"})) +
        card("codex",  renderCodex(data.codex ||{error:"No data"})) +
        card("gemini", renderGemini(data.antigravity||data.gemini||{error:"No data"}));
    }
    const t = data._collected_at ? new Date(data._collected_at*1000) : new Date();
    document.getElementById("meta").textContent =
      "Updated " + t.toLocaleTimeString("en-US",{hour:"2-digit",minute:"2-digit"});
  }catch(e){
    document.getElementById("meta").textContent = "Connection failed";
  }
}
load(false);
setInterval(()=>load(false), 300000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/usage"):
            force = "refresh=1" in self.path
            body = json.dumps(collect(force)).encode()
            self._send(200, "application/json", body)
        elif self.path == "/" or self.path.startswith("/index"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        elif self.path.startswith("/manifest.json"):
            manifest = json.dumps({
                "name": "AI Usage", "short_name": "AI Usage",
                "start_url": "/", "display": "standalone",
                "background_color": "#0e1420", "theme_color": "#0e1420",
                "icons": [{"src": "/icon.png", "sizes": "180x180", "type": "image/png"}],
            }).encode()
            self._send(200, "application/manifest+json", manifest)
        elif self.path.startswith("/icon.png"):
            import base64
            self._send(200, "image/png", base64.b64decode(ICON_B64))
        else:
            self._send(404, "text/plain", b"not found")

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # keep the console quiet
        pass


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    print(f"\n  AI Usage dashboard started")
    print(f"  On this computer:  http://127.0.0.1:{PORT}")
    print(f"  On your phone:     http://{lan_ip()}:{PORT}   (same Wi-Fi)\n")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

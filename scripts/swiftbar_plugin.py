#!/usr/bin/env python3
# <xbar.title>AI Usage</xbar.title>
# <xbar.desc>Claude / Codex / Gemini quota in the menu bar (reads the local dashboard)</xbar.desc>
#
# SwiftBar plugin. Filename "ai_usage.5m.py" = auto-refresh every 5 minutes.
# Requires the AI usage dashboard running at SERVER below.

import json
import urllib.request
from datetime import datetime, timedelta

SERVER = "http://127.0.0.1:8899"  # change if you renamed/moved the server, or want a Tailscale address

OK, WARN, BAD, MUTED = "#28a745", "#e6a700", "#e04b3a", "#8a8a8a"


def tone(remain):
    if remain is None:
        return MUTED
    return OK if remain > 40 else WARN if remain > 15 else BAD


def pct(s):
    try:
        return float(str(s).replace("%", ""))
    except (TypeError, ValueError):
        return None


def text_bar(remain, width=14):
    if remain is None:
        return "·" * width
    filled = round(width * max(0, min(100, remain)) / 100)
    return "█" * filled + "░" * (width - filled)


def rel_to_abs(s):
    """'4h 32m' / '5d 3h' / '45m' -> absolute datetime"""
    if not s:
        return None
    import re
    d = re.search(r"(\d+)\s*d", s)
    h = re.search(r"(\d+)\s*h", s)
    m = re.search(r"(\d+)\s*m", s)
    if not (d or h or m):
        return None
    mins = (int(d.group(1)) * 1440 if d else 0) + (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
    return datetime.now() + timedelta(minutes=mins)


def fmt_abs(dt):
    if dt is None:
        return None
    now = datetime.now()
    t = dt.strftime("%-I:%M %p")
    return t if dt.date() == now.date() else dt.strftime("%a ") + t


def iso_to_abs(ts):
    if not ts:
        return None
    try:
        return fmt_abs(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone())
    except ValueError:
        return None


def line(label, remain, reset, indent="  "):
    r = "—" if remain is None else f"{remain:.0f}%"
    tail = f"   resets {reset}" if reset else ""
    return (f"{indent}{label:<7}{text_bar(remain)}  {r}{tail}"
            f" | font=Menlo size=12 color={tone(remain)} trim=false")


# ---------- fetch ----------
try:
    with urllib.request.urlopen(SERVER + "/api/usage", timeout=20) as resp:
        data = json.loads(resp.read().decode())
except Exception:
    print("AI ⚠️")
    print("---")
    print(f"Dashboard not reachable at {SERVER} | color={BAD}")
    print("Is ai_usage_dashboard.py running? | color=" + MUTED)
    print(f"Open dashboard | href={SERVER}")
    raise SystemExit

c = data.get("claude") or {}
x = data.get("codex") or {}
g = data.get("antigravity") or data.get("gemini") or {}
models = g.get("models") or []
pro = next((m for m in models if "pro" in m.get("name", "").lower()), models[0] if models else None)
flash = next((m for m in models if "flash" in m.get("name", "").lower()),
             models[1] if len(models) > 1 else None)

metrics = [
    ("Claude", "5h",     pct((c.get("five_hour") or {}).get("remaining")),  fmt_abs(rel_to_abs((c.get("five_hour") or {}).get("resets_in")))),
    ("Claude", "Weekly", pct((c.get("seven_day") or {}).get("remaining")),  fmt_abs(rel_to_abs((c.get("seven_day") or {}).get("resets_in")))),
    ("Codex",  "5h",     pct((x.get("primary_window") or {}).get("remaining")),   fmt_abs(rel_to_abs((x.get("primary_window") or {}).get("resets_in")))),
    ("Codex",  "Weekly", pct((x.get("secondary_window") or {}).get("remaining")), fmt_abs(rel_to_abs((x.get("secondary_window") or {}).get("resets_in")))),
    ("Gemini", "Pro",    pro.get("remaining_pct") if pro else None,     iso_to_abs(pro.get("reset_time")) if pro else None),
    ("Gemini", "Flash",  flash.get("remaining_pct") if flash else None, iso_to_abs(flash.get("reset_time")) if flash else None),
]
opus_used = pct((c.get("opus") or {}).get("used")) if c.get("opus") else None
if opus_used is not None:
    metrics.insert(2, ("Claude", "Opus", 100 - opus_used, None))

# ---------- menu bar title: the tightest quota ----------
valid = [m for m in metrics if m[2] is not None]
if valid:
    prov, label, remain, _ = min(valid, key=lambda m: m[2])
    icon = "🟢" if remain > 35 else ("⚡" if remain > 10 else "🔴")
    print(f"AI {icon}{remain:.0f}% | color={tone(remain)}")
else:
    print("AI —")

# ---------- dropdown ----------
print("---")
if valid:
    print(f"Tightest: {prov} {label} — {remain:.0f}% left | color={tone(remain)} size=12")
    print("---")

for prov_name in ("Claude", "Codex", "Gemini"):
    err = {"Claude": c, "Codex": x, "Gemini": g}[prov_name].get("error")
    print(f"{prov_name} | size=13")
    if err:
        print(f"  {err} | color={WARN} size=12")
        continue
    for p_, label, remain_, reset in metrics:
        if p_ == prov_name:
            print(line(label, remain_, reset))
print("---")
print(f"Open dashboard | href={SERVER}")
print("Refresh now | refresh=true")

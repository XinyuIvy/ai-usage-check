// AI Usage Widget (Scriptable) — Medium (compact) + Large (full-height, absolute reset times)
// Setup: 1) Install the free "Scriptable" app from the App Store
//        2) Create a new script and paste this entire file
//        3) Run the script once and enter the stable Tailscale URL printed by install.sh
//        4) Long-press home screen -> add widget -> Scriptable -> Medium or Large
//        5) Select this script. Live data is cached for display while the Mac is off.

const SERVER_KEY = "ai-usage-dashboard-server";

// Save the server URL once instead of editing this file whenever networks change.
async function configuredServer() {
  const parameter = String(args.widgetParameter || "").trim();
  if (parameter) {
    Keychain.set(SERVER_KEY, parameter.replace(/\/$/, ""));
    return parameter.replace(/\/$/, "");
  }
  if (Keychain.contains(SERVER_KEY)) return Keychain.get(SERVER_KEY);
  if (config.runsInApp) {
    const prompt = new Alert();
    prompt.title = "Connect AI Usage";
    prompt.message = "Enter the stable Tailscale URL printed by install.sh, for example http://100.64.0.1:8899";
    prompt.addTextField("http://100.x.x.x:8899");
    prompt.addAction("Save");
    prompt.addCancelAction("Cancel");
    if (await prompt.present() === 0) {
      const value = prompt.textFieldValue(0).trim().replace(/\/$/, "");
      if (value) {
        Keychain.set(SERVER_KEY, value);
        return value;
      }
    }
  }
  return null;
}

const SERVER = await configuredServer();

// ---------- fetch + iCloud-backed fallback ----------
const SNAPSHOT_NAME = "ai_usage_snapshot.json";
const snapshotFM = FileManager.iCloud();
const snapshotPath = snapshotFM.joinPath(snapshotFM.documentsDirectory(), SNAPSHOT_NAME);

async function saveSnapshot(value) {
  try {
    snapshotFM.writeString(snapshotPath, JSON.stringify(value));
  } catch (e) {
    // A live widget still works if iCloud storage is temporarily unavailable.
  }
}

async function loadSnapshot() {
  try {
    if (!snapshotFM.fileExists(snapshotPath)) return null;
    await snapshotFM.downloadFileFromiCloud(snapshotPath);
    const value = JSON.parse(snapshotFM.readString(snapshotPath));
    return value && !value._error ? value : null;
  } catch (e) {
    return null;
  }
}

let data = null;
let source = "none";
try {
  if (!SERVER) throw new Error("Server is not configured");
  const req = new Request(SERVER + "/api/usage");
  req.timeoutInterval = 15;
  const live = await req.loadJSON();
  if (!live || live._error) throw new Error(live?._error || "No live data");
  data = live;
  source = "live";
  await saveSnapshot(live);
} catch (e) {
  data = await loadSnapshot();
  source = data ? "cached" : "none";
}
const cached = source === "cached";

// ---------- helpers ----------
const C = {
  bg: new Color("#0e1420"),
  text: new Color("#e8ecf2"),
  muted: new Color("#7e8aa0"),
  ok: new Color("#3dd6a3"),
  warn: new Color("#f2b84b"),
  bad: new Color("#f06a5d"),
  track: new Color("#26314a"),
};
const isLarge = (config.widgetFamily || "large") === "large";

function pct(s) {
  const n = parseFloat(String(s ?? "").replace("%", ""));
  return isNaN(n) ? null : n;
}
function tone(remain) {
  if (remain == null) return C.muted;
  return remain > 40 ? C.ok : remain > 15 ? C.warn : C.bad;
}
// relative string ("4h 32m", "5d 3h", "45m") -> absolute Date
function relToDate(s) {
  if (!s) return null;
  const d = /(\d+)\s*d/.exec(s), h = /(\d+)\s*h/.exec(s), m = /(\d+)\s*m/.exec(s);
  if (!d && !h && !m) return null;
  const mins = (d ? +d[1] * 1440 : 0) + (h ? +h[1] * 60 : 0) + (m ? +m[1] : 0);
  return new Date(Date.now() + mins * 60000);
}
// absolute Date -> "5:30 PM" (today) or "Wed 5:30 PM" (another day)
function fmtAbs(dt) {
  if (!dt || isNaN(dt)) return null;
  const tf = new DateFormatter();
  tf.useShortTimeStyle();
  const time = tf.string(dt);
  const now = new Date();
  if (dt.getFullYear() === now.getFullYear() && dt.getMonth() === now.getMonth() && dt.getDate() === now.getDate()) {
    return time;
  }
  const wf = new DateFormatter();
  wf.dateFormat = dt - now > 6 * 86400000 ? "M/d" : "EEE";
  return wf.string(dt) + " " + time;
}
function barImage(remain, w, h) {
  const ctx = new DrawContext();
  ctx.size = new Size(w, h);
  ctx.opaque = false;
  ctx.respectScreenScale = true;
  ctx.setFillColor(C.track);
  const track = new Path();
  track.addRoundedRect(new Rect(0, 0, w, h), h / 2, h / 2);
  ctx.addPath(track);
  ctx.fillPath();
  const r = Math.max(0, Math.min(100, remain ?? 0));
  if (r > 0) {
    ctx.setFillColor(tone(remain));
    const fill = new Path();
    fill.addRoundedRect(new Rect(0, 0, Math.max(h, (w * r) / 100), h), h / 2, h / 2);
    ctx.addPath(fill);
    ctx.fillPath();
  }
  return ctx.getImage();
}

// ---------- collect metrics ----------
const c = data?.claude || {};
const x = data?.codex || {};
const g = data?.antigravity || data?.gemini || {};
const models = Array.isArray(g.models) ? g.models : [];
const proM = models.find((m) => m.name.toLowerCase().includes("pro")) || models[0];
const flashM = models.find((m) => m.name.toLowerCase().includes("flash")) || models[1];

// unified metric list: {prov, label, remain, resetAt(Date)}
const METRICS = [
  { prov: "Claude", label: "5h",     remain: pct(c.five_hour?.remaining), resetAt: relToDate(c.five_hour?.resets_in) },
  { prov: "Claude", label: "Weekly", remain: pct(c.seven_day?.remaining), resetAt: relToDate(c.seven_day?.resets_in) },
  ...(() => {
    const wins = [x.primary_window, x.secondary_window].filter(Boolean).map((win) => {
      const at = relToDate(win.resets_in);
      const isWeekly = (at && at - Date.now() > 86400000) || /d/.test(String(win.window || ""));
      return { prov: "Codex", label: isWeekly ? "Weekly" : "5h", remain: pct(win.remaining), resetAt: at };
    });
    for (const lbl of ["5h", "Weekly"])
      if (!wins.some((win) => win.label === lbl)) wins.push({ prov: "Codex", label: lbl, remain: null, resetAt: null });
    return wins.sort((a, b) => (a.label === "5h" ? -1 : 1));
  })(),
  { prov: "Gemini", label: proM ? "Pro" : "—",     remain: proM ? proM.remaining_pct : null,     resetAt: proM?.reset_time ? new Date(proM.reset_time) : null },
  { prov: "Gemini", label: flashM ? "Flash" : "—", remain: flashM ? flashM.remaining_pct : null, resetAt: flashM?.reset_time ? new Date(flashM.reset_time) : null },
];
if (c.opus) {
  const u = pct(c.opus.used);
  METRICS.splice(2, 0, { prov: "Claude", label: "Opus", remain: u == null ? null : 100 - u, resetAt: null });
}

// fun verdict line: find the tightest quota
function verdict() {
  const valid = METRICS.filter((m) => m.remain != null);
  if (!valid.length) return { icon: "🤔", text: "No quota data yet" };
  const min = valid.reduce((a, b) => (b.remain < a.remain ? b : a));
  if (min.remain <= 10) return { icon: "🔴", text: `${min.prov} ${min.label} almost empty — ${min.remain.toFixed(0)}% left`, color: C.bad };
  if (min.remain <= 40) return { icon: "⚡", text: `Tightest: ${min.prov} ${min.label} — ${min.remain.toFixed(0)}% left`, color: C.warn };
  return { icon: "🟢", text: "All tanks full — go build", color: C.ok };
}

// ---------- build widget ----------
const w = new ListWidget();
w.backgroundColor = C.bg;
w.setPadding(15, 16, 13, 16);
if (SERVER) w.url = SERVER;
w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);

const title = w.addStack();
title.centerAlignContent();
const t = title.addText("AI Usage");
t.font = Font.boldSystemFont(isLarge ? 15 : 13);
t.textColor = C.text;
title.addSpacer();
const df = new DateFormatter();
df.dateFormat = "HH:mm";
const collectedAt = data?._collected_at ? new Date(data._collected_at * 1000) : null;
const ageMinutes = collectedAt ? Math.max(0, Math.floor((Date.now() - collectedAt) / 60000)) : null;
const ageText = ageMinutes == null ? "unknown age"
  : ageMinutes < 1 ? "just now"
  : ageMinutes < 60 ? ageMinutes + "m ago"
  : ageMinutes < 1440 ? Math.floor(ageMinutes / 60) + "h ago"
  : Math.floor(ageMinutes / 1440) + "d ago";
const statusText = cached
  ? "cached · " + ageText
  : source === "live"
    ? "updated " + df.string(collectedAt || new Date())
    : "offline";
const ts = title.addText(statusText);
ts.font = Font.systemFont(10);
ts.textColor = cached ? C.warn : source === "live" ? C.muted : C.bad;

if (!data) {
  w.addSpacer(10);
  const e = w.addText("Can't reach the dashboard on your computer");
  e.font = Font.systemFont(12);
  e.textColor = C.warn;
  const h = w.addText(SERVER
    ? "No saved snapshot yet. Turn on the Mac and refresh once."
    : "Open this script once in Scriptable to save the Tailscale URL");
  h.font = Font.systemFont(10);
  h.textColor = C.muted;
  w.addSpacer();
} else if (isLarge) {
  // ===== LARGE: name column left, data right; flexible gaps fill the height =====
  const NAME_W = 64;
  const BAR_W = 216;

  w.addSpacer(8);
  const v = verdict();
  const vTxt = w.addText(v.icon + " " + v.text);
  vTxt.font = Font.mediumSystemFont(12);
  vTxt.textColor = v.color || C.muted;
  vTxt.lineLimit = 1;

  const provs = ["Claude", "Codex", "Gemini"];
  for (const prov of provs) {
    w.addSpacer();  // flexible gap -> spreads blocks over full height

    const block = w.addStack();
    block.layoutHorizontally();
    block.centerAlignContent();

    const nameCol = block.addStack();
    nameCol.layoutVertically();
    nameCol.size = new Size(NAME_W, 0);
    const name = nameCol.addText(prov);
    name.font = Font.semiboldSystemFont(14);
    name.textColor = C.text;
    name.lineLimit = 1;

    block.addSpacer(8);

    const dataCol = block.addStack();
    dataCol.layoutVertically();
    const ms = METRICS.filter((m) => m.prov === prov);
    for (let j = 0; j < ms.length; j++) {
      const m = ms[j];
      const line = dataCol.addStack();
      const lab = line.addText(m.label);
      lab.font = Font.systemFont(11);
      lab.textColor = C.muted;
      lab.lineLimit = 1;
      line.addSpacer();
      const abs = fmtAbs(m.resetAt);
      const right = line.addText(
        (m.remain == null ? "—" : m.remain.toFixed(0) + "%") + (abs ? " · resets " + abs : "")
      );
      right.font = Font.mediumSystemFont(11);
      right.textColor = tone(m.remain);
      right.lineLimit = 1;
      dataCol.addSpacer(3);
      const img = dataCol.addImage(barImage(m.remain, BAR_W, 7));
      img.imageSize = new Size(BAR_W, 7);
      if (j < ms.length - 1) dataCol.addSpacer(7);
    }
  }
  w.addSpacer();  // bottom flexible gap
} else {
  // ===== MEDIUM: compact two-column rows =====
  w.addSpacer(8);
  function addRow(name, ms) {
    const row = w.addStack();
    row.layoutHorizontally();
    row.centerAlignContent();
    const nameTxt = row.addText(name);
    nameTxt.font = Font.semiboldSystemFont(12);
    nameTxt.textColor = C.text;
    nameTxt.lineLimit = 1;
    row.addSpacer();
    for (const m of ms) {
      const col = row.addStack();
      col.layoutVertically();
      col.size = new Size(118, 0);
      const top = col.addStack();
      const lab = top.addText(m.label + " ");
      lab.font = Font.systemFont(10);
      lab.textColor = C.muted;
      const val = top.addText(m.remain == null ? "—" : m.remain.toFixed(0) + "%");
      val.font = Font.mediumSystemFont(10);
      val.textColor = tone(m.remain);
      col.addSpacer(2);
      const img = col.addImage(barImage(m.remain, 110, 5));
      img.imageSize = new Size(110, 5);
      row.addSpacer(6);
    }
  }
  const by = (prov) => METRICS.filter((m) => m.prov === prov && m.label !== "Opus").slice(0, 2);
  addRow("Claude", by("Claude"));
  w.addSpacer(8);
  addRow("Codex", by("Codex"));
  w.addSpacer(8);
  addRow("Gemini", by("Gemini"));
}

Script.setWidget(w);
if (config.runsInApp) w.presentLarge();
Script.complete();

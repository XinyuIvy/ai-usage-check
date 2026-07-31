// AI Usage — Übersicht desktop widget
// Install: Übersicht menu bar icon -> Open Widgets Folder -> drop this file in.
// Shows Claude / Codex / Gemini quota, always visible on the desktop.

export const command = "curl -s --max-time 20 http://127.0.0.1:8899/api/usage";

export const refreshFrequency = 300000; // 5 minutes

// position & card style — tweak top/right to move it around the desktop
export const className = `
  top: 24px;
  right: 24px;
  width: 300px;
  font-family: -apple-system, Helvetica, sans-serif;
  color: #e8ecf2;
  background: rgba(14, 20, 32, 0.82);
  border: 1px solid rgba(38, 49, 74, 0.9);
  border-radius: 16px;
  padding: 16px 18px 14px;
  backdrop-filter: blur(12px);
`;

const MUTED = "#7e8aa0";
const tone = (r) => (r == null ? MUTED : r > 40 ? "#3dd6a3" : r > 15 ? "#f2b84b" : "#f06a5d");
const pct = (s) => {
  const n = parseFloat(String(s ?? "").replace("%", ""));
  return isNaN(n) ? null : n;
};
const relToDate = (s) => {
  if (!s) return null;
  const d = /(\d+)\s*d/.exec(s), h = /(\d+)\s*h/.exec(s), m = /(\d+)\s*m/.exec(s);
  if (!d && !h && !m) return null;
  const mins = (d ? +d[1] * 1440 : 0) + (h ? +h[1] * 60 : 0) + (m ? +m[1] : 0);
  return new Date(Date.now() + mins * 60000);
};
const fmtAbs = (dt) => {
  if (!dt || isNaN(dt)) return null;
  const now = new Date();
  const time = dt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (dt.toDateString() === now.toDateString()) return time;
  if (dt - now > 6 * 86400000)
    return dt.toLocaleDateString([], { month: "numeric", day: "numeric" }) + " " + time;
  return dt.toLocaleDateString([], { weekday: "short" }) + " " + time;
};

const Bar = ({ remain }) => (
  <div style={{ height: 6, borderRadius: 3, background: "#0a0f1a", overflow: "hidden", marginTop: 3 }}>
    <div style={{ height: "100%", width: `${Math.max(1.5, Math.min(100, remain ?? 0))}%`, background: tone(remain), borderRadius: 3 }} />
  </div>
);

const Metric = ({ label, remain, reset }) => (
  <div style={{ marginBottom: 7 }}>
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
      <span style={{ color: MUTED }}>{label}</span>
      <span style={{ color: tone(remain), fontWeight: 600 }}>
        {remain == null ? "—" : `${Math.round(remain)}%`}
        {reset ? <span style={{ color: MUTED, fontWeight: 400 }}> · resets {reset}</span> : null}
      </span>
    </div>
    <Bar remain={remain} />
  </div>
);

export const render = ({ output }) => {
  let data = null;
  try {
    data = JSON.parse(output);
  } catch (e) {
    /* server down */
  }
  if (!data) {
    return (
      <div>
        <div style={{ fontSize: 13, fontWeight: 700 }}>AI Usage</div>
        <div style={{ fontSize: 11, color: "#f2b84b", marginTop: 6 }}>
          Dashboard not reachable — is ai_usage_dashboard.py running?
        </div>
      </div>
    );
  }

  const c = data.claude || {};
  const x = data.codex || {};
  const g = data.antigravity || data.gemini || {};
  const models = Array.isArray(g.models) ? g.models : [];
  const pro = models.find((m) => m.name.toLowerCase().includes("pro")) || models[0];
  const flash = models.find((m) => m.name.toLowerCase().includes("flash")) || models[1];

  const metrics = [
    { prov: "Claude", label: "5h", remain: pct(c.five_hour?.remaining), reset: fmtAbs(relToDate(c.five_hour?.resets_in)) },
    { prov: "Claude", label: "Weekly", remain: pct(c.seven_day?.remaining), reset: fmtAbs(relToDate(c.seven_day?.resets_in)) },
    ...(() => {
      const wins = [x.primary_window, x.secondary_window].filter(Boolean).map((w) => {
        const at = relToDate(w.resets_in);
        const isWeekly = (at && at - Date.now() > 86400000) || /d/.test(String(w.window || ""));
        return { prov: "Codex", label: isWeekly ? "Weekly" : "5h", remain: pct(w.remaining), reset: fmtAbs(at) };
      });
      for (const lbl of ["5h", "Weekly"])
        if (!wins.some((w) => w.label === lbl)) wins.push({ prov: "Codex", label: lbl, remain: null, reset: null });
      return wins.sort((a, b) => (a.label === "5h" ? -1 : 1));
    })(),
    { prov: "Gemini", label: pro ? "Pro" : "—", remain: pro ? pro.remaining_pct : null, reset: pro?.reset_time ? fmtAbs(new Date(pro.reset_time)) : null },
    { prov: "Gemini", label: flash ? "Flash" : "—", remain: flash ? flash.remaining_pct : null, reset: flash?.reset_time ? fmtAbs(new Date(flash.reset_time)) : null },
  ];
  if (c.opus) {
    const u = pct(c.opus.used);
    metrics.splice(2, 0, { prov: "Claude", label: "Opus", remain: u == null ? null : 100 - u, reset: null });
  }

  const valid = metrics.filter((m) => m.remain != null);
  const min = valid.length ? valid.reduce((a, b) => (b.remain < a.remain ? b : a)) : null;
  const verdict = !min
    ? { icon: "🤔", text: "No quota data yet", color: MUTED }
    : min.remain <= 10
    ? { icon: "🔴", text: `${min.prov} ${min.label} almost empty — ${Math.round(min.remain)}% left`, color: "#f06a5d" }
    : min.remain <= 40
    ? { icon: "⚡", text: `Tightest: ${min.prov} ${min.label} — ${Math.round(min.remain)}% left`, color: "#f2b84b" }
    : { icon: "🟢", text: "All tanks full — go build", color: "#3dd6a3" };

  const updated = data._collected_at
    ? new Date(data._collected_at * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>AI Usage</span>
        <span style={{ fontSize: 10, color: MUTED }}>updated {updated}</span>
      </div>
      <div style={{ fontSize: 11, color: verdict.color, margin: "7px 0 11px" }}>
        {verdict.icon} {verdict.text}
      </div>
      {["Claude", "Codex", "Gemini"].map((prov) => (
        <div key={prov} style={{ marginBottom: 9 }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 5 }}>{prov}</div>
          {metrics
            .filter((m) => m.prov === prov)
            .map((m) => (
              <Metric key={prov + m.label} label={m.label} remain={m.remain} reset={m.reset} />
            ))}
        </div>
      ))}
    </div>
  );
};

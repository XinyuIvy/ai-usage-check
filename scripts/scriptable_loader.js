// AI Usage Widget loader. Install this file once; widget updates are automatic.

const OWNER = "XinyuIvy";
const REPO = "ai-usage-check";
const BRANCH = "main";
const REMOTE_URL = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/scripts/scriptable_widget.js`;
const SERVER_KEY = "ai-usage-dashboard-server";
const UPDATE_KEY = "ai-usage-widget-last-update";
const UPDATE_INTERVAL_MS = 24 * 60 * 60 * 1000;
const fm = FileManager.iCloud();
const docs = fm.documentsDirectory();
const activePath = fm.joinPath(docs, "AI Usage.runtime.js");
const backupPath = fm.joinPath(docs, "AI Usage.runtime.backup.js");
const configPath = fm.joinPath(docs, "ai_usage_config.json");

// Import configuration written automatically by the Mac installer.
if (fm.fileExists(configPath)) {
  try {
    await fm.downloadFileFromiCloud(configPath);
    const saved = JSON.parse(fm.readString(configPath));
    if (saved.server_url) Keychain.set(SERVER_KEY, String(saved.server_url).replace(/\/$/, ""));
  } catch (error) {
    console.log(`Could not read Mac configuration: ${error}`);
  }
}

async function refreshRuntime() {
  const last = Keychain.contains(UPDATE_KEY) ? Number(Keychain.get(UPDATE_KEY)) : 0;
  if (fm.fileExists(activePath) && Date.now() - last < UPDATE_INTERVAL_MS) return;
  try {
    const request = new Request(REMOTE_URL);
    request.timeoutInterval = 15;
    const source = await request.loadString();
    if (!source.includes("AI Usage Widget") || source.length < 1000) throw new Error("Invalid update");
    if (fm.fileExists(backupPath)) fm.remove(backupPath);
    if (fm.fileExists(activePath)) fm.copy(activePath, backupPath);
    fm.writeString(activePath, source);
    Keychain.set(UPDATE_KEY, String(Date.now()));
  } catch (error) {
    console.log(`Widget update skipped: ${error}`);
  }
}

await refreshRuntime();
if (!fm.fileExists(activePath) && fm.fileExists(backupPath)) fm.copy(backupPath, activePath);

if (!fm.fileExists(activePath)) {
  const widget = new ListWidget();
  widget.addText("AI Usage").font = Font.boldSystemFont(14);
  widget.addText("Open once while online to finish setup.").textColor = Color.gray();
  Script.setWidget(widget);
  if (!config.runsInWidget) await widget.presentMedium();
  Script.complete();
} else {
  await fm.downloadFileFromiCloud(activePath);
  const source = fm.readString(activePath);
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  try {
    await new AsyncFunction(source)();
  } catch (error) {
    if (!fm.fileExists(backupPath)) throw error;
    await fm.downloadFileFromiCloud(backupPath);
    await new AsyncFunction(fm.readString(backupPath))();
  }
}


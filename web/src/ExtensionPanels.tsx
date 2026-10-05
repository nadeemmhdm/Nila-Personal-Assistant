import {useInlineConfirm} from './InlineConfirm';
import React, { useEffect, useState } from "react";
import {
  Plus,
  RefreshCw,
  Play,
  Pause,
  Trash2,
  PenLine,
  ShieldCheck,
  Download,
  Terminal,
  Check,
} from "lucide-react";
async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json();
  if (!r.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check the fields and try again",
    );
  return data;
}
type Job = {
  id?: string;
  title: string;
  prompt: string;
  kind: string;
  interval_minutes: number;
  next_run: number;
  enabled: boolean | number;
  running_until?: number;
  missed_policy?: string;
};
const fresh = (): Job => ({
  title: "",
  prompt: "",
  kind: "ai",
  interval_minutes: 0,
  next_run: Date.now() / 1000 + 3600,
  enabled: true,
  missed_policy: "ask",
});
function localTime(epoch: number) {
  const d = new Date(epoch * 1000);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
export function SystemPanel() {
  const {ask,confirmation}=useInlineConfirm();
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [update, setUpdate] = useState<any>(null),
    [model, setModel] = useState("llama3.2:1b"),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  const fail = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  const refresh = () => api("/system").then(setData).catch(fail);
  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);
  async function check() {
    setBusy(true);
    try {
      setUpdate(await api("/update"));
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function install() {
    if (
      !(await ask(
        "Download and build the latest GitHub main-branch code? Your next launch will use the new version.",
      ))
    )
      return;
    try {
      await api("/update", "POST");
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function pull() {
    try {
      await api("/models/pull", "POST", { model });
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function service(action: string) {
    try {
      setMessage((await api("/worker/" + action, "POST")).message);
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  return (
    <div className="page-scroll">
      <section className="settings-page">{confirmation}
        <div className="eyebrow">KEEP NILA FEELING AT HOME</div>
        <h1>Your local system.</h1>
        <p>Diagnostics, downloads, updates and background work—in one place.</p>
        {error && (
          <div role="alert" className="error-banner">
            {error}
          </div>
        )}
        {message && <p role="status">{message}</p>}
        <div className="panel">
          <h2>
            <ShieldCheck size={18} />
            Health & privacy
          </h2>
          {data ? (
            <>
              <dl className="system-grid">
                <dt>Version</dt>
                <dd>{data.version}</dd>
                <dt>Ollama</dt>
                <dd>{data.ollama_online ? "Connected" : "Unavailable"}</dd>
                <dt>Default model</dt>
                <dd>
                  {data.model} · {data.model_ready ? "Ready" : "Missing"}
                </dd>
                <dt>Storage encryption</dt>
                <dd>
                  {data.encrypted ? "Enabled" : "Off"} · {data.key_protection}
                </dd>
                <dt>Background worker</dt>
                <dd>
                  {data.worker.running ? "Running" : "Not running"} · Telegram connection is managed by Nila
                </dd>
                <dt>Data folder</dt>
                <dd>{data.storage}</dd>
              </dl>
              {data.error && <p>{data.error}</p>}
            </>
          ) : (
            <p>Checking…</p>
          )}
          <button className="text-button" onClick={refresh}>
            <RefreshCw size={14} />
            Run diagnostics
          </button>
          <p>
            Encrypted data is readable by Nila while signed in. Protect your
            operating-system account and keep your encryption key.
          </p>
        </div>
        <div className="panel">
          <h2>
            <Download size={18} />
            Model download
          </h2>
          <label>
            Ollama model name
            <input
              maxLength={120}
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </label>
          <button
            className="primary"
            disabled={data?.maintenance.pull.status === "running" || !model}
            onClick={pull}
          >
            Download / resume
          </button>
          <p>
            Requires internet and running Ollama. Installed models:{" "}
            {data?.models.map((m: any) => m.name).join(", ") || "None detected"}
          </p>
          <p role="status">
            {data?.maintenance.pull.status} {data?.maintenance.pull.message}{" "}
            {data?.maintenance.pull.progress?.status}
            {data?.maintenance.pull.progress?.total
              ? ` · ${Math.round((100 * (data.maintenance.pull.progress.completed || 0)) / data.maintenance.pull.progress.total)}%`
              : ""}
          </p>
        </div>
        <div className="panel">
          <h2>
            <RefreshCw size={18} />
            Updates from GitHub
          </h2>
          <p>
            Uses main-branch commits, independently of releases. Automatic
            checks run at startup at most once a day when enabled in
            Preferences. New code activates on the next launch.
          </p>
          <p>
            {data?.installation.managed
              ? "Managed Windows installation"
              : "Source install: pull code and rebuild, or use the Windows installer."}
          </p>
          <button className="text-button" disabled={busy} onClick={check}>
            {busy ? "Checking…" : "Check for updates"}
          </button>
          <button
            className="primary"
            disabled={
              !data?.installation.managed ||
              data?.maintenance.update.status === "running"
            }
            onClick={install}
          >
            Install latest commit
          </button>
          {update && (
            <p>
              {update.message}{" "}
              {update.latest && `Latest: ${update.latest.slice(0, 8)}`}{" "}
              {update.available ? "New commit available." : ""}
            </p>
          )}
          <p role="status">{data?.maintenance.update.message}</p>
        </div>
        <div className="panel">
          <h2>
            <Terminal size={18} />
            Telegram background connection
          </h2>
          <p>
            The Windows installer registers a per-user login task. Start/stop
            controls affect that worker. Disable Telegram in Workspace to stop
            the connection everywhere, including this open Web UI.
          </p>
          <div className="job-actions">
            {["start", "stop", "enable", "disable"].map((action) => (
              <button
                key={action}
                className="text-button"
                disabled={data?.platform !== "Windows"}
                onClick={() => service(action)}
              >
                {action === "enable"
                  ? "Enable at login"
                  : action === "disable"
                    ? "Disable at login"
                    : action + " worker"}
              </button>
            ))}
          </div>
          <p>
            From the terminal: <code>nila worker</code>. Telegram needs an
            awake computer, internet, Ollama, and an enabled connection.
          </p>
        </div>
      </section>
    </div>
  );
}

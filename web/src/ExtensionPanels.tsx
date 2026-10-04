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
};
const fresh = (): Job => ({
  title: "",
  prompt: "",
  kind: "ai",
  interval_minutes: 0,
  next_run: Date.now() / 1000 + 3600,
  enabled: true,
});
function localTime(epoch: number) {
  const d = new Date(epoch * 1000);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
export function Automations() {
  const [data, setData] = useState<{ jobs: Job[]; runs: any[]; worker: any }>({
      jobs: [],
      runs: [],
      worker: {},
    }),
    [draft, setDraft] = useState<Job>(fresh),
    [instruction, setInstruction] = useState(""),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [info, setInfo] = useState("");
  const fail = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  const refresh = () => api("/automations").then(setData).catch(fail);
  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, []);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api(
        "/automations" + (draft.id ? "/" + draft.id : ""),
        draft.id ? "PUT" : "POST",
        { ...draft, enabled: !!draft.enabled },
      );
      setDraft(fresh());
      setInfo("Automation saved. Results appear below.");
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function action(id: string, action: string) {
    setError("");
    try {
      if (action === "delete") {
        if (!confirm("Delete this automation and its run history?")) return;
        await api("/automations/" + id, "DELETE");
      } else await api("/automations/" + id + "/" + action, "POST");
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function generate() {
    setLoading(true);
    setError("");
    try {
      const j = await api<Job>("/automations/draft", "POST", { instruction });
      setDraft({ ...j, enabled: true });
      setInfo(
        "Draft created. Review the task and schedule, then Save to enable it.",
      );
    } catch (e) {
      fail(e);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="page-scroll">
      <section className="settings-page">
        <div className="eyebrow">OFFLINE, ON YOUR SCHEDULE</div>
        <h1>A little help, automatically.</h1>
        <p>
          Assign local work to Nila. This window runs the scheduler while open;
          the Windows login worker keeps it running after you close the window.
          Your computer must be awake.
        </p>
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        {info && <p role="status">{info}</p>}
        <div className="panel">
          <h2>Describe the task</h2>
          <label>
            Ask Nila to draft an automation
            <textarea
              value={instruction}
              maxLength={2000}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Every morning, summarize my notes and unfinished tasks."
            />
          </label>
          <button
            className="primary"
            disabled={loading || instruction.trim().length < 5}
            onClick={generate}
          >
            {loading ? "Drafting locally…" : "Create draft"}
          </button>
          <p>The model creates a draft. You choose when it runs.</p>
        </div>
        <form className="panel" onSubmit={save}>
          <h2>{draft.id ? "Edit automation" : "New automation"}</h2>
          <label>
            Title
            <input
              required
              maxLength={100}
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
          </label>
          <div className="form-grid">
            <label>
              Action
              <select
                value={draft.kind}
                onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
              >
                <option value="ai">Write with local AI</option>
                <option value="brief">Summarize local notes & tasks</option>
                <option value="note">Save a note</option>
                <option value="task">Create a to-do</option>
              </select>
            </label>
            <label>
              Repeat every (minutes; 0 = once)
              <input
                type="number"
                required
                min={0}
                max={525600}
                value={draft.interval_minutes}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    interval_minutes: Number(e.target.value),
                  })
                }
              />
            </label>
          </div>
          <label>
            Instructions / text
            <textarea
              required
              maxLength={4000}
              value={draft.prompt}
              onChange={(e) => setDraft({ ...draft, prompt: e.target.value })}
            />
          </label>
          <label>
            Next run (your local time)
            <input
              required
              type="datetime-local"
              value={localTime(draft.next_run)}
              onChange={(e) => {
                if (e.target.value)
                  setDraft({
                    ...draft,
                    next_run: new Date(e.target.value).getTime() / 1000,
                  });
              }}
            />
          </label>
          <label className="check-label">
            <input
              type="checkbox"
              checked={!!draft.enabled}
              onChange={(e) =>
                setDraft({ ...draft, enabled: e.target.checked })
              }
            />
            Enable this automation
          </label>
          <button className="primary">
            <Check size={15} />
            Save automation
          </button>
          {draft.id && (
            <button
              type="button"
              className="text-button"
              onClick={() => setDraft(fresh())}
            >
              Cancel edit
            </button>
          )}
          <p>
            Repeats use elapsed minutes; 1,440 means every 24 hours, not a
            timezone-aware calendar rule. Minimum repeating interval: 5 minutes.
          </p>
        </form>
        <h2 className="section-label">Scheduled work</h2>
        {!data.jobs.length && <p className="muted">No automations yet.</p>}
        {data.jobs.map((job) => (
          <div className="panel" key={job.id}>
            <div className="job-heading">
              <strong>{job.title}</strong>
              <span className="muted">
                {(job.running_until || 0) > Date.now() / 1000
                  ? "Running"
                  : job.enabled
                    ? "Scheduled"
                    : "Paused"}
              </span>
            </div>
            <p>{job.prompt}</p>
            <p>
              {job.kind} ·{" "}
              {job.interval_minutes
                ? `Every ${job.interval_minutes} minutes`
                : "Once"}{" "}
              · {new Date(job.next_run * 1000).toLocaleString()}
            </p>
            <div className="job-actions">
              <button
                className="text-button"
                onClick={() => action(job.id!, "run")}
              >
                <Play size={14} />
                Run now
              </button>
              <button
                className="text-button"
                onClick={() => action(job.id!, "pause")}
              >
                <Pause size={14} />
                Pause / stop
              </button>
              <button
                className="text-button"
                onClick={() => {
                  setDraft({ ...job, enabled: !!job.enabled });
                  setInfo("Editing " + job.title);
                }}
              >
                <PenLine size={14} />
                Edit / resume
              </button>
              <button
                className="text-button"
                onClick={() => action(job.id!, "delete")}
              >
                <Trash2 size={14} />
                Delete
              </button>
            </div>
          </div>
        ))}
        <h2 className="section-label">Run history</h2>
        {data.runs.map((run) => (
          <details className="panel" key={run.id}>
            <summary>
              {data.jobs.find((j) => j.id === run.automation_id)?.title ||
                "Automation"}{" "}
              · {run.status} · {new Date(run.started * 1000).toLocaleString()}
            </summary>
            <pre className="run-output">{run.output || "Working…"}</pre>
            <button
              className="text-button"
              onClick={() => {
                const u = URL.createObjectURL(
                  new Blob([run.output], { type: "text/plain" }),
                );
                const a = document.createElement("a");
                a.href = u;
                a.download = "nila-automation.txt";
                a.click();
                setTimeout(() => URL.revokeObjectURL(u), 1000);
              }}
            >
              Download result
            </button>
          </details>
        ))}
      </section>
    </div>
  );
}
export function SystemPanel() {
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
      !confirm(
        "Download and build the latest GitHub main-branch code? Your next launch will use the new version.",
      )
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
      <section className="settings-page">
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
                  {data.worker.running ? "Running" : "Not running"} · Web
                  scheduler is active
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
            Background automation
          </h2>
          <p>
            The Windows installer registers a per-user login task. Start/stop
            controls affect that worker; this open Web UI continues to run its
            scheduler. Pause individual jobs to stop them everywhere.
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
            From the terminal: <code>nila worker</code>. Offline jobs need an
            awake computer; missed schedules resume once when Nila next runs.
          </p>
        </div>
      </section>
    </div>
  );
}

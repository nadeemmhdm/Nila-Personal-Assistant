import React, { useEffect, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Play,
  Square,
  KeyRound,
  RefreshCw,
  Trash2,
  Download,
  Brain,
  Check,
  PenLine,
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
  const d = await r.json();
  if (!r.ok)
    throw Error(
      typeof d.detail === "string"
        ? d.detail
        : "Check your input and try again.",
    );
  return d;
}
export function LearningLab() {
  const [key, setKey] = useState(""),
    [configured, setConfigured] = useState(false),
    [geminiModels, setGeminiModels] = useState<any[]>([]),
    [localModels, setLocalModels] = useState<any[]>([]);
  const [topic, setTopic] = useState(""),
    [description, setDescription] = useState(""),
    [model, setModel] = useState("llama3.2:1b"),
    [gemini, setGemini] = useState(""),
    [minutes, setMinutes] = useState(15),
    [rounds, setRounds] = useState(10),
    [consent, setConsent] = useState(false),
    [save, setSave] = useState(true);
  const [history, setHistory] = useState<any[]>([]),
    [selected, setSelected] = useState<string | null>(null),
    [session, setSession] = useState<any>(null),
    [lessons, setLessons] = useState<any[]>([]),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [edit, setEdit] = useState<string | null>(null),
    [editText, setEditText] = useState("");
  const fail = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  async function refresh() {
    const [h, k] = await Promise.all([
      api("/learning/sessions"),
      api("/learning/knowledge"),
    ]);
    setHistory(h);
    setLessons(k);
  }
  useEffect(() => {
    void api("/learning/key")
      .then((d) => setConfigured(d.configured))
      .catch(fail);
    void api("/settings")
      .then((s) => setModel(s.model))
      .catch(fail);
    void api("/status")
      .then((s) => setLocalModels(s.models))
      .catch(fail);
    void refresh().catch(fail);
  }, []);
  useEffect(() => {
    let live = true;
    async function poll() {
      try {
        const h = await api("/learning/sessions");
        if (live) setHistory(h);
        if (selected) {
          const s = await api("/learning/sessions/" + selected);
          if (live) setSession(s);
        }
        const k = await api("/learning/knowledge");
        if (live) setLessons(k);
      } catch (e) {
        if (live) fail(e);
      }
    }
    void poll();
    const timer = setInterval(poll, 1200);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [selected]);
  async function saveKey() {
    setError("");
    try {
      await api("/learning/key", "PUT", { value: key });
      setKey("");
      setConfigured(true);
      setNotice("Key saved encrypted. It is never returned to the browser.");
    } catch (e) {
      fail(e);
    }
  }
  async function removeKey() {
    if (!confirm("Remove the Gemini key and stop active learning sessions?"))
      return;
    try {
      await api("/learning/key", "DELETE");
      setConfigured(false);
      setGeminiModels([]);
      setNotice("Key removed.");
    } catch (e) {
      fail(e);
    }
  }
  async function loadModels() {
    setBusy(true);
    setError("");
    try {
      const data = await api<any[]>("/learning/models");
      setGeminiModels(data);
      if (data.length) setGemini((current) => current || data[0].name);
      setNotice(
        "Models loaded. Check free-tier availability and quota in your Google AI Studio project.",
      );
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function start(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const d = await api("/learning/sessions", "POST", {
        topic,
        description,
        local_model: model,
        gemini_model: gemini,
        minutes,
        max_rounds: rounds,
        save_knowledge: save,
        consent,
      });
      setSelected(d.id);
      setNotice("Learning session started. You can stop it at any time.");
      await refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function stop(id: string) {
    try {
      await api("/learning/sessions/" + id + "/stop", "POST");
      setNotice("Stopping current requests…");
    } catch (e) {
      fail(e);
    }
  }
  async function removeSession(id: string) {
    if (!confirm("Delete this transcript and all lessons saved from it?"))
      return;
    try {
      await api("/learning/sessions/" + id, "DELETE");
      if (selected === id) {
        setSelected(null);
        setSession(null);
      }
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  function download() {
    if (!session) return;
    const text =
      "# " +
      session.config.topic +
      "\n\nStatus: " +
      session.status +
      "\n\n" +
      session.messages
        .map((m: any) => `## ${m.actor} · Round ${m.round}\n\n${m.content}`)
        .join("\n\n");
    const u = URL.createObjectURL(new Blob([text], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = u;
    a.download = "nila-learning-session.md";
    a.click();
    setTimeout(() => URL.revokeObjectURL(u), 1000);
  }
  async function toggle(k: any) {
    try {
      await api("/learning/knowledge/" + k.id, "PUT", {
        content: k.content,
        enabled: !k.enabled,
      });
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function editLesson() {
    try {
      await api("/learning/knowledge/" + edit, "PUT", {
        content: editText,
        enabled: !!lessons.find((k) => k.id === edit)?.enabled,
      });
      setEdit(null);
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function forget(id: string) {
    if (!confirm("Delete this learned lesson?")) return;
    try {
      await api("/learning/knowledge/" + id, "DELETE");
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  const running = history.find((s) => s.status === "running");
  return (
    <div className="page-scroll">
      <section className="settings-page lab-page">
        <div className="eyebrow">TWO MODELS. A VISIBLE CONVERSATION.</div>
        <h1>Learn, review, improve.</h1>
        <p>
          Ollama explains. Gemini reviews. Ollama revises mistakes. Save
          reviewed study notes for relevant future chats—this does not change
          model weights, and Gemini can also be wrong.
        </p>
        {error && (
          <div role="alert" className="error-banner">
            {error}
          </div>
        )}
        {notice && <p role="status">{notice}</p>}
        <details className="panel" open={!configured}>
          <summary>
            <KeyRound size={15} /> Gemini connection ·{" "}
            {configured ? "Key saved" : "Not configured"}
          </summary>
          <label>
            Gemini API key
            <input
              type="password"
              autoComplete="new-password"
              value={key}
              maxLength={300}
              onChange={(e) => setKey(e.target.value)}
              placeholder="Paste your Google AI Studio API key"
            />
          </label>
          <div className="job-actions">
            <button
              className="primary"
              disabled={key.trim().length < 10}
              onClick={saveKey}
            >
              Save key
            </button>
            <button
              className="text-button"
              disabled={!configured || busy}
              onClick={loadModels}
            >
              <RefreshCw size={14} />
              Load available Gemini models
            </button>
            <button
              className="text-button"
              disabled={!configured}
              onClick={removeKey}
            >
              Remove key
            </button>
          </div>
          <p>
            Free-tier limits depend on your project and model. Nila cannot
            guarantee zero cost for a billing-enabled key. Google may use
            unpaid-service content to improve its products; avoid private
            information.{" "}
            <a
              href="https://ai.google.dev/gemini-api/terms"
              target="_blank"
              rel="noreferrer"
            >
              Google data terms
            </a>{" "}
            ·{" "}
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noreferrer"
            >
              Get an API key
            </a>
          </p>
        </details>
        <form className="panel" onSubmit={start}>
          <h2>Start a discussion</h2>
          <label>
            Topic
            <input
              required
              maxLength={200}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Python dictionaries"
            />
          </label>
          <label>
            Description (optional)
            <textarea
              maxLength={4000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Explain common mistakes, review examples and correct misunderstandings."
            />
          </label>
          <div className="form-grid">
            <label>
              Ollama model
              <input
                required
                list="lab-local-models"
                  aria-label="Ollama model"
                value={model}
                maxLength={120}
                onChange={(e) => setModel(e.target.value)}
              />
              <datalist id="lab-local-models">
                {localModels.map((m) => (
                  <option key={m.name} value={m.name} />
                ))}
              </datalist>
            </label>
            <label>
              Gemini reviewer
              <input
                required
                list="lab-gemini-models"
                  aria-label="Gemini reviewer"
                value={gemini}
                maxLength={100}
                onChange={(e) => setGemini(e.target.value)}
                placeholder="Load models or enter a model name"
              />
              <datalist id="lab-gemini-models">
                {geminiModels.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.label}
                  </option>
                ))}
              </datalist>
            </label>
            <label>
              Time limit (minutes)
              <input
                type="number"
                required
                min={1}
                max={60}
                value={minutes}
                onChange={(e) => setMinutes(Number(e.target.value))}
              />
            </label>
            <label>
              Maximum rounds
              <input
                type="number"
                required
                min={1}
                max={40}
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
              />
            </label>
          </div>
          <label className="check-label">
            <input
              type="checkbox"
              checked={save}
              onChange={(e) => setSave(e.target.checked)}
            />
            <span>
              Save Gemini-reviewed lessons for relevant future chats
              <small>
                Inspect, edit, disable or delete them below. Reviews are not
                independent fact checks.
              </small>
            </span>
          </label>
          <label className="check-label">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            <span>
              I allow this topic, description and model conversation to be sent
              to Google.
              <small>
                Personal profile, saved memory and ordinary chat history are not
                included. Gemini requires internet.
              </small>
            </span>
          </label>
          <button
            className="primary"
            disabled={!configured || !consent || busy || !!running}
          >
            <Play size={15} />
            Start learning
          </button>
          <p>
            Stops at the time limit, round limit, Stop, or an error—whichever
            comes first. Each round uses one Gemini request; there is a
            12-second pause between rounds. The lab reserves local generation
            while active.
          </p>
        </form>
        {running && (
          <div className="lab-live">
            <span>
              Running · {running.config.topic} ·{" "}
              {Math.max(
                0,
                Math.ceil((running.deadline - Date.now() / 1000) / 60),
              )}{" "}
              min remaining
            </span>
            <button className="primary" onClick={() => stop(running.id)}>
              <Square size={14} />
              Stop session
            </button>
            <button
              className="text-button"
              onClick={() => setSelected(running.id)}
            >
              View conversation
            </button>
          </div>
        )}
        <h2 className="section-label">Conversations</h2>
        <div className="lab-history">
          {history.map((s) => (
            <div key={s.id}>
              <button
                className={selected === s.id ? "selected" : ""}
                onClick={() => setSelected(s.id)}
              >
                {s.config.topic}
                <small>
                  {s.status} · {new Date(s.started * 1000).toLocaleString()}
                </small>
              </button>
              {s.status !== "running" && (
                <button
                  className="icon"
                  aria-label={"Delete " + s.config.topic}
                  onClick={() => removeSession(s.id)}
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
        {session && (
          <div className="panel lab-transcript">
            <div className="job-heading">
              <strong>
                {session.config.topic} · {session.status}
              </strong>
              <button
                className="icon"
                aria-label="Download transcript"
                onClick={download}
              >
                <Download size={17} />
              </button>
            </div>
            {session.error && <p role="alert">{session.error}</p>}
            {session.messages.map((m: any) => (
              <article className={"lab-turn " + m.actor} key={m.id}>
                <div className="message-meta">
                  {m.actor === "ollama"
                    ? session.config.local_model
                    : m.actor === "gemini"
                      ? "Gemini reviewer"
                      : m.actor === "question"
                        ? "Discussion prompt"
                        : "Learning note"}
                  <small>Round {m.round}</small>
                </div>
                <div className="markdown">
                  <Markdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      img: () => null,
                      a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noreferrer">
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {m.content || "Working…"}
                  </Markdown>
                </div>
              </article>
            ))}
            {session.status === "running" && (
              <p className="responding">Models are discussing…</p>
            )}
          </div>
        )}
        <h2 className="section-label">
          <Brain size={17} /> Learned knowledge
        </h2>
        <p>
          Gemini-reviewed notes, not guaranteed facts. Enabled notes are matched
          to relevant chat questions. Control overall use in Preferences.
        </p>
        {!lessons.length && (
          <p className="muted">No reviewed lessons saved yet.</p>
        )}
        {lessons.map((k) => (
          <div className="panel" key={k.id}>
            <div className="job-heading">
              <strong>{k.topic}</strong>
              <small>{k.enabled ? "Available in chat" : "Disabled"}</small>
            </div>
            {edit === k.id ? (
              <>
                <textarea
                  maxLength={2000}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                />
                <button className="primary" onClick={editLesson}>
                  <Check size={14} />
                  Save lesson
                </button>
                <button className="text-button" onClick={() => setEdit(null)}>
                  Cancel
                </button>
              </>
            ) : (
              <p>{k.content}</p>
            )}
            <div className="job-actions">
              <button className="text-button" onClick={() => toggle(k)}>
                {k.enabled ? "Disable" : "Enable"}
              </button>
              <button
                className="text-button"
                onClick={() => {
                  setEdit(k.id);
                  setEditText(k.content);
                }}
              >
                <PenLine size={14} />
                Edit
              </button>
              <button className="text-button" onClick={() => forget(k.id)}>
                <Trash2 size={14} />
                Forget
              </button>
            </div>
            <p className="hint">Source: Gemini review · Round {k.round}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

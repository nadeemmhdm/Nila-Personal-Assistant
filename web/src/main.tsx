import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUp,
  ArrowUpRight,
  Plus,
  Search,
  MessageSquare,
  Brain,
  NotebookPen,
  CheckCheck,
  Settings2,
  PanelLeftClose,
  Menu,
  X,
  Cpu,
  Terminal,
  ShieldCheck,
  Sun,
  Moon,
  Copy,
  Check,
  Trash2,
  Download,
  Square,
  RefreshCw,
  Sparkles,
  Code2,
  PenLine,
  Compass,
  ChevronDown,
} from "lucide-react";
import "./style.css";

type Settings = {
  assistant_name: string;
  user_name: string;
  model: string;
  language: string;
  temperature: number;
  num_ctx: number;
  memory_enabled: boolean;
};
type Message = { id: number; role: string; content: string; status: string };
type Chat = { id: string; title: string; messages?: Message[] };
type Item = { id: string; content: string; done?: boolean };
type Status = {
  online: boolean;
  model_ready: boolean;
  models: { name: string }[];
  error?: string;
};
type Page = "chat" | "memories" | "notes" | "tasks" | "settings";
const defaults: Settings = {
  assistant_name: "Nila",
  user_name: "",
  model: "llama3.2:1b",
  language: "Auto",
  temperature: 0.7,
  num_ctx: 2048,
  memory_enabled: true,
};
async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Request failed" }));
    throw Error(
      typeof e.detail === "string"
        ? e.detail
        : "Check the values and try again.",
    );
  }
  return r.json();
}
function Orb({
  small = false,
  busy = false,
}: {
  small?: boolean;
  busy?: boolean;
}) {
  return (
    <div
      aria-hidden="true"
      className={`orb ${small ? "small" : ""} ${busy ? "busy" : ""}`}
    >
      <div />
      <i />
      <b />
    </div>
  );
}
function App() {
  const [settings, setSettings] = useState<Settings>(defaults),
    [draft, setDraft] = useState<Settings>(defaults);
  const [status, setStatus] = useState<Status | null>(null),
    [chats, setChats] = useState<Chat[]>([]),
    [chat, setChat] = useState<Chat | null>(null);
  const [page, setPage] = useState<Page>("chat"),
    [input, setInput] = useState(""),
    [busy, setBusy] = useState(false),
    [replyText, setReplyText] = useState("");
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [search, setSearch] = useState(""),
    [mobile, setMobile] = useState(false);
  const [theme, setTheme] = useState(
      () => localStorage.getItem("nila-theme") || "dark",
    ),
    [reduced, setReduced] = useState(
      () => localStorage.getItem("nila-motion") === "reduce",
    );
  const [items, setItems] = useState<Item[]>([]),
    [itemText, setItemText] = useState(""),
    [editId, setEditId] = useState<string | null>(null),
    [copied, setCopied] = useState<number | null>(null);
  const bottom = useRef<HTMLDivElement>(null),
    field = useRef<HTMLTextAreaElement>(null),
    requestChat = useRef<string | null>(null),
    sendLock = useRef(false),
    selection = useRef(0);
  const notify = (text: string) => {
    setNotice(text);
    window.setTimeout(() => setNotice(""), 3000);
  };
  const fail = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  async function refreshStatus() {
    try {
      setStatus(await api<Status>("/status"));
    } catch (e) {
      fail(e);
    }
  }
  async function refreshChats() {
    setChats(await api<Chat[]>("/chats"));
  }
  useEffect(() => {
    Promise.all([api<Settings>("/settings"), api<Chat[]>("/chats")])
      .then(([s, c]) => {
        setSettings(s);
        setDraft(s);
        setChats(c);
      })
      .catch(fail);
    void refreshStatus();
    const id = setInterval(refreshStatus, 30000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("nila-theme", theme);
  }, [theme]);
  useEffect(() => {
    document.documentElement.dataset.motion = reduced ? "reduce" : "full";
    localStorage.setItem("nila-motion", reduced ? "reduce" : "full");
  }, [reduced]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: busy ? "instant" : "smooth" });
  }, [chat?.messages?.length, replyText]);
  useEffect(() => {
    setItemText("");
    setEditId(null);
    if (["memories", "notes", "tasks"].includes(page)) {
      let active = true;
      api<Item[]>("/items/" + page)
        .then((v) => {
          if (active) setItems(v);
        })
        .catch(fail);
      return () => {
        active = false;
      };
    }
  }, [page]);
  function navigate(p: Page) {
    if (busy) return;
    selection.current++;
    setPage(p);
    setError("");
    setMobile(false);
  }
  function newChat() {
    if (busy) return;
    selection.current++;
    setPage("chat");
    setChat(null);
    setInput("");
    setError("");
    setMobile(false);
    field.current?.focus();
  }
  async function openChat(id: string) {
    if (busy) return;
    const ticket = ++selection.current;
    try {
      const value = await api<Chat>("/chats/" + id);
      if (ticket === selection.current) {
        setChat(value);
        setPage("chat");
        setError("");
        setMobile(false);
      }
    } catch (e) {
      fail(e);
    }
  }
  async function send(text = input) {
    if (sendLock.current || !text.trim()) return;
    sendLock.current = true;
    setBusy(true);
    setError("");
    setReplyText("");
    setInput("");
    let active = chat;
    try {
      if (!active) active = await api<Chat>("/chats", "POST");
      requestChat.current = active.id;
      setChat({
        ...active,
        messages: [
          ...(active.messages || []),
          { id: -1, role: "user", content: text, status: "complete" },
        ],
      });
      const r = await fetch("/api/chats/" + active.id + "/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text }),
      });
      if (!r.ok) {
        const d = await r.json();
        throw Error(
          typeof d.detail === "string" ? d.detail : "Message could not be sent",
        );
      }
      const reader = r.body!.getReader(),
        decoder = new TextDecoder();
      let buffer = "",
        sawDone = false;
      const event = (line: string) => {
        if (!line.trim()) return;
        const data = JSON.parse(line);
        if (data.error) setError(data.error);
        if (data.token) setReplyText((t) => t + data.token);
        if (data.done) sawDone = true;
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) event(line);
      }
      buffer += decoder.decode();
      if (buffer.trim()) event(buffer);
      if (!sawDone)
        throw Error(
          "Connection interrupted. Your saved conversation will be restored.",
        );
    } catch (e) {
      fail(e);
      setInput(text);
    } finally {
      if (active) {
        try {
          const saved = await api<Chat>("/chats/" + active.id);
          setChat(saved);
          if (
            !saved.messages?.some(
              (m) => m.role === "user" && m.content === text,
            )
          )
            setInput(text);
          await refreshChats();
        } catch (e) {
          fail(e);
        }
      }
      requestChat.current = null;
      sendLock.current = false;
      setReplyText("");
      setBusy(false);
    }
  }
  async function stop() {
    if (requestChat.current)
      try {
        await api("/chats/" + requestChat.current + "/stop", "POST");
      } catch (e) {
        fail(e);
      }
  }
  async function deleteChat(id: string) {
    if (!confirm("Delete this conversation permanently?")) return;
    try {
      await api("/chats/" + id, "DELETE");
      if (chat?.id === id) newChat();
      await refreshChats();
    } catch (e) {
      fail(e);
    }
  }
  async function copy(content: string, id: number) {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(id);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("Clipboard unavailable. Select and copy the text manually.");
    }
  }
  function exportChat() {
    if (!chat) return;
    const text =
      "# " +
      chat.title +
      "\n" +
      (chat.messages || [])
        .map((m) => `\n## ${m.role} (${m.status})\n\n${m.content}\n`)
        .join("");
    const url = URL.createObjectURL(
      new Blob([text], { type: "text/markdown" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "nila-conversation.md";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    try {
      const s = await api<Settings>("/settings", "PUT", draft);
      setSettings(s);
      setDraft(s);
      notify("Preferences saved");
      void refreshStatus();
    } catch (e) {
      fail(e);
    }
  }
  async function saveItem(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editId) {
        const previous = items.find((i) => i.id === editId);
        await api("/items/" + page + "/" + editId, "PUT", {
          content: itemText,
          done: !!previous?.done,
        });
      } else await api("/items/" + page, "POST", { content: itemText });
      setItemText("");
      setEditId(null);
      setItems(await api<Item[]>("/items/" + page));
    } catch (e) {
      fail(e);
    }
  }
  async function removeItem(id: string) {
    if (!confirm("Delete this item?")) return;
    try {
      await api("/items/" + page + "/" + id, "DELETE");
      setItems(await api<Item[]>("/items/" + page));
    } catch (e) {
      fail(e);
    }
  }
  const nav = [
    { id: "chat", icon: MessageSquare, label: "Conversations" },
    { id: "memories", icon: Brain, label: "Memory" },
    { id: "notes", icon: NotebookPen, label: "Notes" },
    { id: "tasks", icon: CheckCheck, label: "Tasks" },
  ] as const;
  const suggestions = [
    {
      icon: Compass,
      title: "Make a plan",
      sub: "Turn a big idea into small steps",
      prompt:
        "Help me make a realistic plan for my day. Ask me what I need to get done.",
    },
    {
      icon: Code2,
      title: "Build something",
      sub: "A little help with your next idea",
      prompt:
        "Help me build a small coding project. Ask me about my idea and experience.",
    },
    {
      icon: PenLine,
      title: "Find the right words",
      sub: "Write, rewrite, and make it yours",
      prompt:
        "Help me write a clear, friendly message. Ask me who it is for and what I want to say.",
    },
    {
      icon: Sparkles,
      title: "Learn something",
      sub: "Make the complicated feel simple",
      prompt:
        "Help me learn something new. Ask what topic I would like to understand.",
    },
  ];
  return (
    <div className="app">
      <div
        className={`scrim ${mobile ? "show" : ""}`}
        onClick={() => setMobile(false)}
      />
      <aside className={mobile ? "open" : ""}>
        <div className="brand">
          <span className="brand-icon">
            <Sparkles size={23} />
          </span>
          <span>
            nila<span className="brand-dot">.</span>
          </span>
          <button
            className="icon mobile-only"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          >
            <PanelLeftClose size={18} />
          </button>
        </div>
        <div className="brand-caption">YOUR PERSONAL ASSISTANT</div>
        <button className="new-chat" onClick={newChat} disabled={busy}>
          <Plus size={18} />
          New conversation<span>↗</span>
        </button>
        <nav>
          {nav.map((n) => (
            <button
              key={n.id}
              disabled={busy}
              className={page === n.id ? "selected" : ""}
              onClick={() => navigate(n.id)}
            >
              <n.icon size={18} />
              {n.label}
              {n.id === "memories" && <span className="tiny-dot" />}
            </button>
          ))}
        </nav>
        <div className="history-heading">
          RECENT CONVERSATIONS <span>{chats.length}</span>
        </div>
        <label className="search">
          <Search size={15} />
          <input
            aria-label="Search conversations"
            placeholder="Search conversations"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <div className="history">
          {chats
            .filter((c) => c.title.toLowerCase().includes(search.toLowerCase()))
            .map((c) => (
              <div
                className={`history-row ${chat?.id === c.id ? "active" : ""}`}
                key={c.id}
              >
                <button disabled={busy} onClick={() => openChat(c.id)}>
                  <MessageSquare size={14} />
                  <span>{c.title}</span>
                </button>
                <button
                  className="icon"
                  disabled={busy}
                  aria-label={"Delete " + c.title}
                  onClick={() => deleteChat(c.id)}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          {!chats.length && (
            <p>
              Your next idea starts here.
              <br />
              Conversations stay on this device.
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={17} />
            <div>
              Local by default<small>Your space. Your conversations.</small>
            </div>
          </div>
          <button
            className={
              page === "settings" ? "settings-link selected" : "settings-link"
            }
            disabled={busy}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={18} />
            Preferences
          </button>
          <div className="profile">
            <span className="avatar">
              {(settings.user_name || "Y")[0].toUpperCase()}
            </span>
            <div>
              {settings.user_name || "Your workspace"}
              <small>Personal workspace</small>
            </div>
            <button
              className="icon"
              aria-label="Toggle color theme"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </div>
      </aside>
      <main>
        <header>
          <div className="header-left">
            <button
              className="icon mobile-only"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu size={20} />
            </button>
            <span>
              {page === "chat"
                ? "Personal space"
                : page === "memories"
                  ? "Your memory"
                  : page === "settings"
                    ? "Preferences"
                    : page[0].toUpperCase() + page.slice(1)}
            </span>
            <span className="divider">/</span>
            <span className="muted">
              {page === "chat"
                ? "A little clarity, every day"
                : "Make yourself at home"}
            </span>
          </div>
          <button
            className="model-pill"
            disabled={busy}
            onClick={() => navigate("settings")}
          >
            <span
              className={
                "status-dot " +
                (status?.online && status.model_ready ? "ready" : "")
              }
            />
            {settings.model}
            <ChevronDown size={13} />
          </button>
        </header>
        {error && (
          <div role="alert" className="error-banner">
            <span>{error}</span>
            <button
              className="icon"
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {notice && (
          <div className="toast" role="status">
            <Check size={16} />
            {notice}
          </div>
        )}
        {page === "chat" ? (
          <>
            <div className="chat-scroll">
              {!chat?.messages?.length && !busy ? (
                <section className="welcome">
                  <div className="eyebrow">
                    <span /> A SPACE TO THINK, CREATE & EXPLORE
                  </div>
                  <Orb />
                  <h1>
                    {settings.user_name
                      ? `Hello, ${settings.user_name}.`
                      : `Hello, I'm ${settings.assistant_name}.`}
                    <br />
                    <span>What's on your mind?</span>
                  </h1>
                  <p>
                    A fresh idea, a busy day, or a question worth asking.
                    <br />
                    I'm here to help you take the next step.
                  </p>
                  <div className="suggestions">
                    {suggestions.map((s) => (
                      <button
                        key={s.title}
                        onClick={() => {
                          setInput(s.prompt);
                          field.current?.focus();
                        }}
                      >
                        <s.icon size={20} />
                        <ArrowUpRight className="suggest-arrow" size={15} />
                        <strong>{s.title}</strong>
                        <span>{s.sub}</span>
                      </button>
                    ))}
                  </div>
                  {status && !status.model_ready && (
                    <div className="setup-hint">
                      <Cpu size={18} />
                      <div>
                        <strong>
                          {status.online
                            ? "One small step: download your model."
                            : "Let’s connect your local assistant."}
                        </strong>
                        <span>
                          {status.online
                            ? `Run ollama pull ${settings.model}`
                            : "Open Ollama, then download llama3.2:1b."}
                        </span>
                      </div>
                      <button
                        className="icon"
                        aria-label="Check connection"
                        onClick={refreshStatus}
                      >
                        <RefreshCw size={17} />
                      </button>
                    </div>
                  )}
                </section>
              ) : (
                <section className="messages">
                  <div className="conversation-heading">
                    <span>
                      {chat?.title === "New conversation"
                        ? "New conversation"
                        : chat?.title}
                    </span>
                    <button
                      className="icon"
                      disabled={busy}
                      onClick={exportChat}
                      aria-label="Export conversation"
                    >
                      <Download size={17} />
                    </button>
                  </div>
                  {chat?.messages?.map((m, i) => (
                    <article
                      key={m.id + "-" + i}
                      className={"message " + m.role}
                    >
                      <div className="message-avatar">
                        {m.role === "assistant" ? (
                          <Sparkles size={17} />
                        ) : (
                          <span>
                            {(settings.user_name || "Y")[0].toUpperCase()}
                          </span>
                        )}
                      </div>
                      <div className="message-body">
                        <div className="message-meta">
                          {m.role === "assistant"
                            ? settings.assistant_name
                            : "You"}
                          {m.status !== "complete" && (
                            <small>Interrupted</small>
                          )}
                        </div>
                        <div className="markdown">
                          <Markdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              img: () => <em>[External image omitted]</em>,
                              a: ({ children, href }) => (
                                <a href={href} target="_blank" rel="noreferrer">
                                  {children}
                                </a>
                              ),
                            }}
                          >
                            {m.content ||
                              (m.status !== "complete"
                                ? "Response stopped before any text arrived."
                                : "")}
                          </Markdown>
                        </div>
                        <button
                          className="copy icon"
                          aria-label="Copy message"
                          onClick={() => copy(m.content, m.id)}
                        >
                          {copied === m.id ? (
                            <Check size={14} />
                          ) : (
                            <Copy size={14} />
                          )}
                        </button>
                      </div>
                    </article>
                  ))}
                  {busy && (
                    <article className="message assistant">
                      <div className="message-avatar">
                        <Orb small busy />
                      </div>
                      <div className="message-body">
                        <div className="message-meta">
                          {settings.assistant_name}
                          <small className="responding">
                            Responding
                            <span className="dots">
                              <i />
                              <i />
                              <i />
                            </span>
                          </small>
                        </div>
                        {replyText ? (
                          <div className="markdown streaming">
                            <Markdown
                              remarkPlugins={[remarkGfm]}
                              components={{ img: () => null }}
                            >
                              {replyText}
                            </Markdown>
                          </div>
                        ) : (
                          <div className="skeleton">
                            <i />
                            <i />
                          </div>
                        )}
                      </div>
                    </article>
                  )}
                  {!busy && chat?.messages?.length && (
                    <button
                      className="retry"
                      onClick={() => {
                        const last = [...(chat.messages || [])]
                          .reverse()
                          .find((m) => m.role === "user");
                        if (last) {
                          setInput(last.content);
                          field.current?.focus();
                        }
                      }}
                    >
                      <RefreshCw size={13} />
                      Use last prompt again
                    </button>
                  )}
                  <div ref={bottom} />
                </section>
              )}
            </div>
            <div className="composer-area">
              <form
                className="composer"
                onSubmit={(e) => {
                  e.preventDefault();
                  void send();
                }}
              >
                <textarea
                  ref={field}
                  aria-label="Message Nila"
                  value={input}
                  maxLength={12000}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={`Ask ${settings.assistant_name} anything…`}
                  rows={2}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey &&
                      !e.nativeEvent.isComposing
                    ) {
                      e.preventDefault();
                      void send();
                    }
                  }}
                />
                <div className="composer-bottom">
                  <span>
                    <ShieldCheck size={14} />
                    Local conversation
                  </span>
                  <div>
                    <kbd>Shift + Enter for a new line</kbd>
                    {busy ? (
                      <button
                        type="button"
                        className="send stop"
                        aria-label="Stop response"
                        onClick={stop}
                      >
                        <Square size={16} />
                      </button>
                    ) : (
                      <button
                        className="send"
                        aria-label="Send message"
                        disabled={!input.trim()}
                      >
                        <ArrowUp size={20} />
                      </button>
                    )}
                  </div>
                </div>
              </form>
              <div className="footer-note">
                <span>
                  {settings.assistant_name} can make mistakes. Double-check
                  important details.
                </span>
                <span>
                  <Terminal size={12} />
                  Also available in your terminal
                </span>
              </div>
            </div>
          </>
        ) : page === "settings" ? (
          <div className="page-scroll">
            <section className="settings-page">
              <div className="eyebrow">MAKE IT YOURS</div>
              <h1>A familiar kind of helpful.</h1>
              <p>Small preferences. A more personal assistant.</p>
              <form onSubmit={saveSettings}>
                <div className="panel">
                  <h2>
                    <Sparkles size={18} />
                    Identity
                  </h2>
                  <div className="form-grid">
                    <label>
                      Assistant name
                      <input
                        required
                        maxLength={40}
                        value={draft.assistant_name}
                        onChange={(e) =>
                          setDraft({ ...draft, assistant_name: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Your name
                      <input
                        maxLength={60}
                        placeholder="What should I call you?"
                        value={draft.user_name}
                        onChange={(e) =>
                          setDraft({ ...draft, user_name: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Reply language
                      <select
                        value={draft.language}
                        onChange={(e) =>
                          setDraft({ ...draft, language: e.target.value })
                        }
                      >
                        <option>Auto</option>
                        <option>English</option>
                        <option>Malayalam</option>
                      </select>
                    </label>
                  </div>
                </div>
                <div className="panel">
                  <h2>
                    <Cpu size={18} />
                    Local model
                  </h2>
                  <p>No API key needed. Connects to Ollama on this computer.</p>
                  <label>
                    Model name
                    <input
                      required
                      list="models"
                      value={draft.model}
                      onChange={(e) =>
                        setDraft({ ...draft, model: e.target.value })
                      }
                    />
                    <datalist id="models">
                      {status?.models.map((m) => (
                        <option key={m.name} value={m.name} />
                      ))}
                    </datalist>
                  </label>
                  <div className="form-grid">
                    <label>
                      Context size
                      <select
                        value={draft.num_ctx}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            num_ctx: Number(e.target.value),
                          })
                        }
                      >
                        <option value={2048}>2,048 · lighter on memory</option>
                        <option value={4096}>4,096</option>
                        <option value={8192}>8,192 · more RAM</option>
                      </select>
                    </label>
                    <label>
                      Temperature · {draft.temperature}
                      <input
                        type="range"
                        min="0"
                        max="1.5"
                        step="0.1"
                        value={draft.temperature}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            temperature: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  </div>
                  <div className="connection">
                    <span
                      className={
                        "status-dot " + (status?.online ? "ready" : "")
                      }
                    />
                    {status?.online
                      ? "Ollama connected"
                      : "Ollama not connected"}
                    <button
                      type="button"
                      className="text-button"
                      onClick={refreshStatus}
                    >
                      Check again
                    </button>
                  </div>
                  <code className="install-command">
                    ollama pull {draft.model}
                  </code>
                  <p className="hint">
                    Run this in your terminal to download a model. Model
                    downloads require internet.
                  </p>
                </div>
                <div className="panel">
                  <h2>
                    <ShieldCheck size={18} />
                    Memory & appearance
                  </h2>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={draft.memory_enabled}
                      onChange={(e) =>
                        setDraft({ ...draft, memory_enabled: e.target.checked })
                      }
                    />
                    <span>
                      Include saved memory in conversations
                      <small>
                        Only facts you explicitly save. You can edit or delete
                        them anytime.
                      </small>
                    </span>
                  </label>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={reduced}
                      onChange={(e) => setReduced(e.target.checked)}
                    />
                    <span>
                      Reduce animations
                      <small>
                        Also respects your system's motion preference.
                      </small>
                    </span>
                  </label>
                  <p className="hint">
                    Chats are stored locally, without encryption. Use your
                    device account and disk encryption to protect them.
                  </p>
                </div>
                <button className="primary" type="submit">
                  Save preferences
                  <Check size={16} />
                </button>
              </form>
              <div className="cli-card">
                <Terminal size={20} />
                <div>
                  <strong>A little closer to your workflow.</strong>
                  <p>
                    Open your terminal and type <code>nila</code>. Same
                    assistant. Same history.
                  </p>
                </div>
              </div>
            </section>
          </div>
        ) : (
          <div className="page-scroll">
            <section className="items-page">
              <div className="eyebrow">YOUR PERSONAL SPACE</div>
              <h1>
                {page === "memories"
                  ? "The little things that matter."
                  : page === "notes"
                    ? "Give your ideas a home."
                    : "One step at a time."}
              </h1>
              <p>
                {page === "memories"
                  ? "Save useful facts for Nila to remember. Nothing is saved here automatically."
                  : page === "notes"
                    ? "Keep notes close by. Notes are not automatically sent to the model."
                    : "A simple list for what comes next. Tasks do not send reminders."}
              </p>
              <form className="item-form" onSubmit={saveItem}>
                <textarea
                  required
                  maxLength={2000}
                  value={itemText}
                  onChange={(e) => setItemText(e.target.value)}
                  placeholder={
                    page === "memories"
                      ? "For example: I prefer short, practical explanations."
                      : page === "notes"
                        ? "An idea worth keeping…"
                        : "What needs to get done?"
                  }
                />
                <div>
                  {editId && (
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => {
                        setEditId(null);
                        setItemText("");
                      }}
                    >
                      Cancel edit
                    </button>
                  )}
                  <button className="primary" disabled={!itemText.trim()}>
                    <Plus size={16} />
                    {editId
                      ? "Save changes"
                      : page === "memories"
                        ? "Save memory"
                        : page === "notes"
                          ? "Add note"
                          : "Add task"}
                  </button>
                </div>
              </form>
              <div className="item-list">
                {!items.length && (
                  <div className="empty-state">
                    <NotebookPen size={28} />
                    <h3>A fresh page.</h3>
                    <p>
                      Add your first{" "}
                      {page === "memories"
                        ? "memory"
                        : page === "notes"
                          ? "note"
                          : "task"}{" "}
                      above.
                    </p>
                  </div>
                )}
                {items.map((item) => (
                  <article
                    className={"item-card " + (item.done ? "done" : "")}
                    key={item.id}
                  >
                    {page === "tasks" && (
                      <input
                        type="checkbox"
                        aria-label={"Complete " + item.content}
                        checked={!!item.done}
                        onChange={async () => {
                          try {
                            await api("/items/tasks/" + item.id, "PUT", {
                              ...item,
                              done: !item.done,
                            });
                            setItems(await api<Item[]>("/items/tasks"));
                          } catch (e) {
                            fail(e);
                          }
                        }}
                      />
                    )}
                    <p>{item.content}</p>
                    <button
                      className="icon"
                      aria-label="Edit item"
                      onClick={() => {
                        setEditId(item.id);
                        setItemText(item.content);
                      }}
                    >
                      <PenLine size={15} />
                    </button>
                    <button
                      className="icon"
                      aria-label="Delete item"
                      onClick={() => removeItem(item.id)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </article>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

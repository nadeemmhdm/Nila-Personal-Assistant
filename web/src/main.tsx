import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { RichText } from "./RichText";
import {
  ThumbsUp,
  ThumbsDown,
  Globe,
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
import { Automations, SystemPanel } from "./ExtensionPanels";
import { LearningLab } from "./LearningLab";

type Settings = {
  assistant_name: string;
  user_name: string;
  model: string;
  language: string;
  temperature: number;
  num_ctx: number;
  memory_enabled: boolean;
  auto_memory: boolean;
  auto_update: boolean;
  description: string;
  position: string;
  completion_year: string;
  company: string;
  job_role: string;
  knowledge_enabled: boolean;
  course: string;
  interests: string;
  tone: string;
};
type Message = {
  id: number;
  role: string;
  content: string;
  status: string;
  rating?: number;
};
type Chat = { id: string; title: string; messages?: Message[] };
type Item = { id: string; content: string; done?: boolean; source?: string };
type Status = {
  online: boolean;
  model_ready: boolean;
  models: { name: string }[];
  error?: string;
};
type Page =
  | "chat"
  | "memories"
  | "notes"
  | "tasks"
  | "settings"
  | "automations"
  | "system"
  | "learning";
const defaults: Settings = {
  assistant_name: "Nila",
  user_name: "",
  model: "llama3.2:1b",
  language: "Auto",
  temperature: 0.7,
  num_ctx: 2048,
  memory_enabled: true,
  auto_memory: true,
  auto_update: true,
  description: "",
  position: "Other",
  completion_year: "",
  company: "",
  job_role: "",
  knowledge_enabled: true,
  course: "",
  interests: "",
  tone: "Friendly",
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
  const [searchMode, setSearchMode] = useState("off");
  const [searchQuery, setSearchQuery] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [feedbackId, setFeedbackId] = useState<number | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackRating, setFeedbackRating] = useState(0);
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
    setEditing(null);
    setFeedbackId(null);
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
        setEditing(null);
        setFeedbackId(null);
        setPage("chat");
        setError("");
        setMobile(false);
      }
    } catch (e) {
      fail(e);
    }
  }
  async function send(text = input, editMessageId: number | null = null) {
    if (sendLock.current || !text.trim()) return;
    sendLock.current = true;
    setBusy(true);
    setError("");
    setReplyText("");
    setInput("");
    setEditing(null);
    let active = chat;
    try {
      if (!active) active = await api<Chat>("/chats", "POST");
      requestChat.current = active.id;
      setChat({
        ...active,
        messages: [
          ...(editMessageId
            ? (active.messages || []).filter((m) => m.id < editMessageId)
            : active.messages || []),
          { id: -1, role: "user", content: text, status: "complete" },
        ],
      });
      const r = await fetch("/api/chats/" + active.id + "/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text,
          search_mode: searchMode,
          search_query:
            searchMode !== "off" && searchQuery.trim()
              ? searchQuery.trim()
              : null,
          edit_message_id: editMessageId,
        }),
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
  async function rate(mid: number, rating: number, reason = "") {
    if (!chat) return;
    try {
      await api(`/chats/${chat.id}/messages/${mid}/feedback`, "PUT", {
        rating,
        reason,
      });
      setChat(await api<Chat>("/chats/" + chat.id));
      setFeedbackId(null);
      notify(
        rating
          ? "Saved locally. Nila will use this feedback in future replies."
          : "Feedback removed.",
      );
    } catch (e) {
      fail(e);
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
    { id: "learning", icon: Brain, label: "Learning Lab" },
    { id: "memories", icon: Brain, label: "Memory" },
    { id: "notes", icon: NotebookPen, label: "Notes" },
    { id: "tasks", icon: CheckCheck, label: "Tasks" },
    { id: "automations", icon: RefreshCw, label: "Automations" },
    { id: "system", icon: Terminal, label: "System" },
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
                            : "Open Ollama and install your preferred model (recommended: llama3.2:1b)."}
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
                          <RichText
                            text={
                              m.content ||
                              (m.status !== "complete"
                                ? "Response stopped before any text arrived."
                                : "")
                            }
                          />
                        </div>
                        {editing === m.id && (
                          <div className="edit-prompt">
                            <textarea
                              aria-label="Edit prompt"
                              value={editText}
                              maxLength={12000}
                              onChange={(e) => setEditText(e.target.value)}
                            />
                            <small>
                              This replaces this answer and removes later turns
                              in this conversation.
                            </small>
                            <div>
                              <button
                                disabled={busy || !editText.trim()}
                                onClick={() => send(editText, m.id)}
                              >
                                Save & regenerate
                              </button>
                              <button onClick={() => setEditing(null)}>
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}
                        <div className="message-actions">
                          <button
                            className="icon"
                            aria-label={
                              m.role === "user"
                                ? "Copy prompt"
                                : "Copy response"
                            }
                            onClick={() => copy(m.content, m.id)}
                          >
                            {copied === m.id ? (
                              <Check size={14} />
                            ) : (
                              <Copy size={14} />
                            )}
                          </button>
                          {m.role === "user" && (
                            <button
                              className="icon"
                              aria-label="Edit prompt"
                              disabled={busy || m.id < 0}
                              onClick={() => {
                                setEditing(m.id);
                                setEditText(m.content);
                              }}
                            >
                              <PenLine size={14} />
                            </button>
                          )}
                          {m.role === "assistant" && (
                            <>
                              <button
                                className={
                                  "icon " + (m.rating === 1 ? "selected" : "")
                                }
                                aria-label="Helpful response"
                                aria-pressed={m.rating === 1}
                                disabled={busy}
                                onClick={() =>
                                  rate(m.id, m.rating === 1 ? 0 : 1)
                                }
                              >
                                <ThumbsUp size={14} />
                              </button>
                              <button
                                className={
                                  "icon " + (m.rating === -1 ? "selected" : "")
                                }
                                aria-label="Unhelpful response"
                                aria-pressed={m.rating === -1}
                                disabled={busy}
                                onClick={() =>
                                  rate(m.id, m.rating === -1 ? 0 : -1)
                                }
                              >
                                <ThumbsDown size={14} />
                              </button>
                              <button
                                className="feedback-link"
                                disabled={busy}
                                onClick={() => {
                                  setFeedbackId(m.id);
                                  setFeedbackText("");
                                  setFeedbackRating(m.rating || -1);
                                }}
                              >
                                Add feedback
                              </button>
                            </>
                          )}
                        </div>
                        {feedbackId === m.id && (
                          <div className="edit-prompt">
                            <textarea
                              aria-label="Feedback guidance"
                              value={feedbackText}
                              maxLength={500}
                              placeholder="What should Nila improve? e.g. Shorter answers, explain with examples."
                              onChange={(e) => setFeedbackText(e.target.value)}
                            />
                            <div>
                              <button
                                disabled={busy || !feedbackText.trim()}
                                onClick={() =>
                                  rate(m.id, feedbackRating, feedbackText)
                                }
                              >
                                Save feedback
                              </button>
                              <button onClick={() => setFeedbackId(null)}>
                                Cancel
                              </button>
                            </div>
                            <small>
                              Stored locally; never sent to Gemini. Adapts
                              future context, not model weights.
                            </small>
                          </div>
                        )}
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
                            {searchMode === "off"
                              ? "Responding"
                              : "Searching & composing"}
                            <span className="dots">
                              <i />
                              <i />
                              <i />
                            </span>
                          </small>
                        </div>
                        {replyText ? (
                          <div className="markdown streaming">
                            <RichText text={replyText} />
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
                          setEditing(last.id);
                          setEditText(last.content);
                        }
                      }}
                    >
                      <RefreshCw size={13} />
                      Edit last prompt
                    </button>
                  )}
                  {!busy && !!chat?.messages?.length && (
                    <button
                      className="retry"
                      onClick={() =>
                        send(
                          "Continue your previous answer from where you left off, without repeating it.",
                        )
                      }
                    >
                      <MessageSquare size={13} />
                      Continue response
                    </button>
                  )}
                  <div ref={bottom} />
                </section>
              )}
            </div>
            <div className="composer-area">
              <div className="search-controls">
                <Globe size={15} />
                <label htmlFor="search-mode">Web search</label>
                <select
                  id="search-mode"
                  value={searchMode}
                  disabled={busy}
                  onChange={(e) => setSearchMode(e.target.value)}
                >
                  <option value="off">Off · local only</option>
                  <option value="quick">Quick search</option>
                  <option value="deep">Deep search</option>
                </select>
                <span>
                  {searchMode === "off"
                    ? "No web queries sent"
                    : searchMode === "quick"
                      ? "One lookup · up to 4 sources"
                      : "Three queries · up to 8 sources"}
                </span>
              </div>
              {searchMode !== "off" && (
                <div className="search-query">
                  <input
                    aria-label="Web search query"
                    maxLength={500}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Optional separate search query"
                    disabled={busy}
                  />
                  <small>
                    Only this query (or your new message if blank) goes to
                    search services. Saved chats, profile and memory are
                    excluded. Internet required.
                  </small>
                </div>
              )}
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
        ) : page === "learning" ? (
          <LearningLab />
        ) : page === "automations" ? (
          <Automations />
        ) : page === "system" ? (
          <SystemPanel />
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
                <div className="panel profile-fields">
                  <h2>Your profile</h2>
                  <label>
                    About you
                    <textarea
                      maxLength={1000}
                      value={draft.description}
                      onChange={(e) =>
                        setDraft({ ...draft, description: e.target.value })
                      }
                      placeholder="Tell Nila a little about yourself, your goals, and how you like to learn."
                    />
                  </label>
                  <div className="form-grid">
                    <label>
                      Position
                      <select
                        aria-label="Position"
                        value={draft.position}
                        onChange={(e) =>
                          setDraft({ ...draft, position: e.target.value })
                        }
                      >
                        <option>Student</option>
                        <option>Employee</option>
                        <option>Self-employed</option>
                        <option>Other</option>
                        <option>Prefer not to say</option>
                      </select>
                    </label>
                    {draft.position === "Student" && (
                      <>
                        <label>
                          Course
                          <input
                            maxLength={150}
                            value={draft.course}
                            onChange={(e) =>
                              setDraft({ ...draft, course: e.target.value })
                            }
                          />
                        </label>
                        <label>
                          Completion year
                          <input
                            placeholder="2027"
                            inputMode="numeric"
                            maxLength={4}
                            pattern="[0-9]{4}|"
                            value={draft.completion_year}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                completion_year: e.target.value,
                              })
                            }
                          />
                        </label>
                      </>
                    )}
                    {["Employee", "Self-employed"].includes(draft.position) && (
                      <>
                        <label>
                          Company name
                          <input
                            maxLength={150}
                            value={draft.company}
                            onChange={(e) =>
                              setDraft({ ...draft, company: e.target.value })
                            }
                          />
                        </label>
                        <label>
                          Job role
                          <input
                            maxLength={150}
                            value={draft.job_role}
                            onChange={(e) =>
                              setDraft({ ...draft, job_role: e.target.value })
                            }
                          />
                        </label>
                      </>
                    )}
                    <label>
                      Interests
                      <input
                        maxLength={500}
                        value={draft.interests}
                        onChange={(e) =>
                          setDraft({ ...draft, interests: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Conversation style
                      <select
                        value={draft.tone}
                        onChange={(e) =>
                          setDraft({ ...draft, tone: e.target.value })
                        }
                      >
                        <option>Friendly</option>
                        <option>Professional</option>
                        <option>Concise</option>
                      </select>
                    </label>
                  </div>
                </div>
                <div className="panel">
                  <h2>
                    <Cpu size={18} />
                    Local model
                  </h2>
                  <p>
                    llama3.2:1b is recommended, not required. Select any
                    compatible Ollama text-chat model. Local models need no API
                    key; cloud-tagged models use Ollama’s own cloud access and
                    require internet.
                  </p>
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
                        You can inspect, edit, or delete saved facts anytime.
                      </small>
                    </span>
                  </label>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={draft.auto_memory}
                      onChange={(e) =>
                        setDraft({ ...draft, auto_memory: e.target.checked })
                      }
                    />
                    <span>
                      Automatically learn useful facts
                      <small>
                        Local AI extracts explicit, non-sensitive facts from
                        short personal statements. Review them in Memory.
                      </small>
                    </span>
                  </label>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={draft.auto_update}
                      onChange={(e) =>
                        setDraft({ ...draft, auto_update: e.target.checked })
                      }
                    />
                    <span>
                      Automatically update from GitHub main
                      <small>
                        Managed Windows installations check at startup, at most
                        once a day. Restart to use the new version.
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
                    Chats, profile, and saved content are encrypted locally.
                    Keep your encryption key and protect your device account.
                  </p>
                </div>
                <label className="check-label panel">
                  <input
                    type="checkbox"
                    checked={draft.knowledge_enabled}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        knowledge_enabled: e.target.checked,
                      })
                    }
                  />
                  <span>
                    Use relevant Learning Lab notes in chat
                    <small>
                      Model-reviewed knowledge can contain mistakes. Manage
                      individual lessons in Learning Lab.
                    </small>
                  </span>
                </label>
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
                  ? "Review facts you saved and facts Nila learned automatically. Delete or correct anything that is wrong."
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
                    <p>
                      {page === "memories" && (
                        <small className="memory-source">
                          {item.source === "automatic"
                            ? "Learned automatically · review accuracy"
                            : "Saved by you"}
                        </small>
                      )}
                      {item.content}
                    </p>
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

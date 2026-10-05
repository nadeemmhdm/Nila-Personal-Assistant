import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { Workspace, ChatWorkspace } from "./Workspace";
import { VoiceInput, speak } from "./Voice";
import { RichText } from "./RichText";
import {
  FileText,
  Paperclip,
  History,
  FolderOpen,
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

import { LearningLab } from "./LearningLab";

type Settings = {
  thinking_level: "low" | "medium" | "high";
  memory_review: boolean;
  setup_complete: boolean;
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
  goals: string;
  response_style: string;
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
type Chat = { temporary?: boolean; id: string; title: string; messages?: Message[] };
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
  | "learning"
  | "workspace";
const defaults: Settings = {
  thinking_level: "medium",
  memory_review: true,
  setup_complete: false,
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
  goals: "",
  response_style: "Balanced",
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

  const [editing, setEditing] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [feedbackId, setFeedbackId] = useState<number | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [regenerateBox,setRegenerateBox]=useState<number|null>(null),[regenerateText,setRegenerateText]=useState(""),[regenerating,setRegenerating]=useState<number|null>(null);
  const [sidebarHidden,setSidebarHidden]=useState(false),[historyView,setHistoryView]=useState(false);
  const [followupQuestions,setFollowupQuestions]=useState<string[]>([]),[attachmentNames,setAttachmentNames]=useState<{id:string;name:string}[]>([]),[uploading,setUploading]=useState(false);
  const fileInput=useRef<HTMLInputElement>(null);
  const [confirmation,setConfirmation]=useState<{message:string;resolve:(v:boolean)=>void}|null>(null);
  const confirmAction=(message:string)=>new Promise<boolean>(resolve=>setConfirmation({message,resolve}));
  const [progress,setProgress]=useState(""),[started,setStarted]=useState(0),[elapsed,setElapsed]=useState(0);
  const [sources,setSources]=useState<{id:number;items:any[]}|null>(null);
  const sourceTicket=useRef(0);
  useEffect(()=>{const close=(e:Event)=>{if(e instanceof KeyboardEvent ? e.key==='Escape' : !(e.target instanceof Element&&e.target.closest('[data-source-region]'))){sourceTicket.current++;setSources(null)}};document.addEventListener('pointerdown',close);document.addEventListener('keydown',close);return()=>{document.removeEventListener('pointerdown',close);document.removeEventListener('keydown',close)}},[]);
  useEffect(()=>{sourceTicket.current++;let live=true;if(chat?.id)api<{id:string;name:string}[]>(`/chats/${chat.id}/attachments`).then(v=>{if(live)setAttachmentNames(v)}).catch(()=>{});return()=>{live=false}},[chat?.id]);
  async function toggleSources(mid:number){if(sources?.id===mid){sourceTicket.current++;setSources(null);return}const ticket=++sourceTicket.current;setSources({id:mid,items:[]});try{const items=await api<any[]>(`/chats/${chat!.id}/messages/${mid}/sources`);if(ticket===sourceTicket.current)setSources({id:mid,items})}catch(e){if(ticket===sourceTicket.current){setSources(null);fail(e)}}}
  async function removeAttachment(id:string){if(!chat)return;try{await api(`/chats/${chat.id}/attachments/${id}`,'DELETE');setAttachmentNames(v=>v.filter(x=>x.id!==id))}catch(e){fail(e)}}

  const [brief,setBrief]=useState<any>(null);
  const mini=new URLSearchParams(location.search).has("mini");
  useEffect(()=>{const handler=(e:KeyboardEvent)=>{if(e.ctrlKey&&e.shiftKey&&e.code==='Space'){e.preventDefault();window.open('/?mini=1','nila-mini','popup,width=460,height=700')}};window.addEventListener('keydown',handler);return ()=>window.removeEventListener('keydown',handler)},[]);
  useEffect(()=>{if(!busy)return;const id=setInterval(()=>setElapsed(Math.floor((Date.now()-started)/1000)),1000);return ()=>clearInterval(id)},[busy,started]);
  useEffect(()=>{api<any>('/brief').then(setBrief).catch(()=>{})},[page]);
  const bottom = useRef<HTMLDivElement>(null),
    field = useRef<HTMLTextAreaElement>(null),
    requestChat = useRef<string | null>(null),
    sendLock = useRef(false),
    selection = useRef(0);
  const notify = (text: string) => {
    setNotice(text);

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
        if(!s.setup_complete&&!mini)setPage("workspace");
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
    setPage(p);setNotice('');
    if(p==="settings")api<Settings>("/settings").then(s=>{setSettings(s);setDraft(s)}).catch(fail);
    setError("");
    setMobile(false);
    setFollowupQuestions([]);
  }
  function newChat() {
    if (busy) return;
    selection.current++;
    setPage("chat");
    if(chat?.temporary)void api("/chats/"+chat.id,"DELETE").catch(fail);
    setChat(null);
    setFollowupQuestions([]);setAttachmentNames([]);setRegenerateBox(null);setSources(null);
    setEditing(null);
    setFeedbackId(null);
    setInput("");
    setError("");
    setMobile(false);
    field.current?.focus();
  }
  useEffect(()=>{const reload=()=>{api<Settings>('/settings').then(s=>{setSettings(s);setDraft(s)}).catch(fail)};window.addEventListener('nila-settings-changed',reload);return()=>window.removeEventListener('nila-settings-changed',reload)},[]);
  async function temporaryChat(){
    if(busy)return;
    selection.current++;setFollowupQuestions([]);setAttachmentNames([]);setSources(null);
    try { if(chat?.temporary)await api('/chats/'+chat.id,'DELETE');const c=await api<Chat>('/chats','POST',{temporary:true});setChat(c);setPage('chat');setInput('');setEditing(null);setRegenerateBox(null);setError('');setMobile(false);setSearchMode('off'); }
    catch(e){fail(e)}
  }
  async function openChat(id: string) {
    if (busy) return;
    const ticket = ++selection.current;
    try {
      if(chat?.temporary&&chat.id!==id)await api("/chats/"+chat.id,"DELETE");
      const value = await api<Chat>("/chats/" + id);
      if (ticket === selection.current) {
        setChat(value);
        setFollowupQuestions([]);setAttachmentNames([]);setRegenerateBox(null);setSources(null);
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
  async function send(text = input, editMessageId: number | null = null, approved=false, regenerateId:number|null=null, instruction="") {
    if (sendLock.current || uploading) return;
    if(!text.trim()&&attachmentNames.length)text="Summarize the attached files: "+attachmentNames.map(x=>x.name).join(", ");
    if(!text.trim())return;

    selection.current++;
    sendLock.current = true;
    setFollowupQuestions([]);
    setStarted(Date.now());setElapsed(0);setProgress('Checking local model');setRegenerating(regenerateId);setRegenerateBox(null);setSources(null);
    setBusy(true);
    setError("");
    setReplyText("");
    if(!regenerateId)setInput("");
    setEditing(null);
    let active = chat;
    try {
      if (!active) active = await api<Chat>("/chats", "POST");
      requestChat.current = active.id;
      if(!regenerateId)setChat({
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
          search_mode: regenerateId ? "off" : searchMode,
          regenerate_id: regenerateId,
          instruction,
          preserve_branch: true,
          thinking_level: settings.thinking_level,
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
        if(data.progress)setProgress(data.progress);
        if(data.stopped&&regenerateId)notify("Regeneration stopped. Original answer kept.");
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

    } finally {
      if (active) {
        try {
          const saved = await api<Chat>("/chats/" + active.id);
          setChat(saved);

          await refreshChats();
        } catch (e) {
          fail(e);
        }
      }
      requestChat.current = null;
      sendLock.current = false;
      setReplyText("");
      setBusy(false);
      setRegenerating(null);
      if(active){const id=active.id,ticket=selection.current;api<string[]>(`/chats/${id}/followups`,'POST').then(q=>{if(requestChat.current===null&&ticket===selection.current)setFollowupQuestions(q)}).catch(()=>{});}
    }
  }
  async function attachFile(file:File){
    setError('');setUploading(true);setNotice('Reading file locally…');
    try{
      if(file.size>5*1024*1024)throw Error('File limit: 5 MB');
      let active=chat;if(!active){active=await api<Chat>('/chats','POST');setChat(active);}
      const data=await new Promise<string>((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=reject;r.readAsDataURL(file)});
      const attachment=await api<{id:string;name:string}>(`/chats/${active.id}/attachments`,'POST',{name:file.name,data});
      setAttachmentNames(n=>[...n.filter(x=>x.id!==attachment.id),attachment]);notify('File attached. Ask a question about it.');await refreshChats();
    }catch(e){fail(e);setNotice('')}finally{setUploading(false)}
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
    if (!await confirmAction("Delete this conversation permanently?")) return;
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
    if (!await confirmAction("Delete this item?")) return;
    try {
      await api("/items/" + page + "/" + id, "DELETE");
      setItems(await api<Item[]>("/items/" + page));
    } catch (e) {
      fail(e);
    }
  }
  const nav = [
    { id: "chat", icon: MessageSquare, label: "Chat" },
    { id: "workspace", icon: FolderOpen, label: "Workspace" },
    { id: "learning", icon: Brain, label: "Learning Lab" },
    { id: "memories", icon: Brain, label: "Memory" },
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
    <div className={"app"+(mini?" mini-app":"")+(sidebarHidden?" sidebar-collapsed":"")}>
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
            className="icon"
            aria-label="Hide sidebar"
            onClick={() => {setMobile(false);setSidebarHidden(true)}}
          >
            <PanelLeftClose size={18} />
          </button>
        </div>
        <div className="brand-caption">YOUR PERSONAL ASSISTANT</div>
        <button className="new-chat" onClick={newChat} disabled={busy}>
          <Plus size={18} />
          New conversation<span>↗</span>
        </button>
        <button className="temporary-button" disabled={busy} onClick={temporaryChat}><ShieldCheck size={15}/>Temporary chat</button>
        <div className="sidebar-switch"><button className={!historyView?'active':''} onClick={()=>setHistoryView(false)}>Explore</button><button className={historyView?'active':''} onClick={()=>setHistoryView(true)}><History size={14}/>History</button></div>
        {!historyView&&<nav>
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
        </nav>}
        {historyView&&<><div className="history-heading">
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
        </>}
        <div className="sidebar-bottom">
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
        {mini&&<div className="mini-toolbar"><strong>Mini Nila</strong><button onClick={newChat}>New</button><button onClick={temporaryChat}>Temporary</button><a href="/" target="_blank" rel="noreferrer">Full workspace</a></div>}
        <header>
          <div className="header-left">
            <button
              className="icon"
              aria-label="Toggle sidebar"
              onClick={() => {setSidebarHidden(!sidebarHidden);setMobile(!mobile)}}
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
        {confirmation&&<div className="section-confirm" role="region" aria-label="Confirm action"><p>{confirmation.message}</p><button onClick={()=>{confirmation.resolve(true);setConfirmation(null)}}>Confirm</button><button onClick={()=>{confirmation.resolve(false);setConfirmation(null)}}>Cancel</button></div>}
        {notice && (
          <div className="section-notice" role="status">
            <Check size={16} />
            {notice}
          </div>
        )}
        {page === "chat" ? (
          <>
            <div className="chat-scroll">
              {chat&&<ChatWorkspace cid={chat.id} temporary={chat.temporary} busy={busy}/>}
              {!chat?.messages?.length && !busy ? (
                <section className="welcome">
                  <div className="eyebrow">
                    <span /> A SPACE TO THINK, CREATE & EXPLORE
                  </div>
                  <Orb />
                  {brief&&<button className="brief-chip" onClick={()=>navigate('workspace')}>Today · {brief.conversations} conversations · {brief.pending_memories} memories to review</button>}
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
                        <div className="message-bubble"><div className="message-meta">
                          {m.role === "assistant"
                            ? settings.assistant_name
                            : "You"}
                          {m.status !== "complete" && (
                            <small>Interrupted</small>
                          )}
                        </div>
                        <div className={"markdown"+(regenerating===m.id?" streaming":"")}>
                          {regenerating===m.id&&!replyText?<div className="skeleton"><i/><i/></div>:<RichText
                            text={
                              (regenerating===m.id?replyText:m.content) ||
                              (m.status !== "complete"
                                ? "Response stopped before any text arrived."
                                : "")
                            }
                          />}
                          {regenerating===m.id&&<small role="status">{progress} · {elapsed}s</small>}
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
                              The original conversation is kept as a branch. This replaces the answer and later turns here.
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
                        </div>
                        {m.role==='assistant'&&<div className="response-tools">
                          <button className="icon" aria-label="Regenerate response" title="Regenerate response" disabled={busy} onClick={()=>{setRegenerateBox(m.id);setRegenerateText('')}}><RefreshCw size={15}/></button>
                          <button data-source-region aria-expanded={sources?.id===m.id} disabled={busy} onClick={()=>toggleSources(m.id)}><Globe size={14}/>Sources</button><button onClick={()=>{try{speak(m.content)}catch(e){fail(e)}}}>Read aloud</button>
                        </div>}
                        {regenerateBox===m.id&&<div className="edit-prompt"><label>What should change? (optional)<textarea aria-label="Regeneration instructions" maxLength={2000} value={regenerateText} onChange={e=>setRegenerateText(e.target.value)} placeholder="e.g. Correct the second example, or explain in simpler words"/></label><small>Only this answer is regenerated locally, in the same place. The original conversation is saved as a branch; later turns move there. If stopped or failed, your original stays. No new web query is sent.</small><div><button disabled={busy} onClick={()=>send('Regenerate this response',null,true,m.id,regenerateText)}>Regenerate answer</button><button onClick={()=>setRegenerateBox(null)}>Cancel</button></div></div>}
                        {sources?.id===m.id&&<div className="source-explanation" data-source-region><strong>Context supplied to this answer</strong><p>This shows supplied references, not proof of the model's reasoning or factual accuracy.</p>{sources.items.length?sources.items.map((source,i)=><div key={i}><b>{source.kind}</b> · {source.label}{source.page?` · page ${source.page}`:''}{source.url&&<a href={source.url} target="_blank" rel="noreferrer">Open source</a>}</div>):<p>No recorded references for this answer.</p>}<button onClick={()=>{sourceTicket.current++;setSources(null)}}>Close references</button></div>}
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
                          {m.role === "assistant" && !chat?.temporary && (
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
                              
                            </>
                          )}
                        </div>

                      </div>
                    </article>
                  ))}
                  {busy && !regenerating && (
                    <article className="message assistant">
                      <div className="message-avatar">
                        <Orb small busy />
                      </div>
                      <div className="message-body">
                        <div className="message-meta">
                          {settings.assistant_name}
                          <small className="responding">
                            {progress} · {elapsed}s
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
                  {!busy&&followupQuestions.length>0&&<div className="followup-questions"><small>Explore next</small>{followupQuestions.map(q=><button key={q} onClick={()=>send(q)}>{q}<ArrowUpRight size={13}/></button>)}</div>}
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
                {attachmentNames.length>0&&<div className="attachment-chips">{attachmentNames.map(n=><span key={n.id}><FileText size={12}/>{n.name}<button type="button" aria-label={"Remove "+n.name} disabled={busy||uploading} onClick={()=>removeAttachment(n.id)}><X size={12}/></button></span>)}</div>}
                <div className="composer-bottom">
                  <div className="composer-tools">
                    <button type="button" className="icon" aria-label="Attach file" disabled={busy||uploading} onClick={()=>fileInput.current?.click()}><Paperclip size={17}/></button>
                    <input ref={fileInput} type="file" hidden accept=".pdf,.txt,.md,.csv,.json,.py,.js,.ts,.html,.css" onChange={e=>{const f=e.target.files?.[0];if(f)void attachFile(f);e.target.value=''}}/>
                    <VoiceInput disabled={busy||uploading} onText={text=>setInput(v=>(v+" "+text).trim())} onError={message=>setError(message)}/><select aria-label="Search mode" value={searchMode} disabled={busy} onChange={e=>setSearchMode(e.target.value)}><option value="off">Web off</option><option value="quick">Quick search</option><option value="deep">Deep search</option></select>
                    <select aria-label="Thinking level" value={settings.thinking_level} disabled={busy} onChange={async e=>{const thinking_level=e.target.value as Settings['thinking_level'];try{const s=await api<Settings>('/settings','PUT',{...await api<Settings>('/settings'),thinking_level});setSettings(s);setDraft(s)}catch(err){fail(err)}}}><option value="low">Think · Low</option><option value="medium">Think · Medium</option><option value="high">Think · High</option></select>
                    <select aria-label="Local model" value={settings.model} disabled={busy} onChange={async e=>{try{const s=await api<Settings>('/settings','PUT',{...await api<Settings>('/settings'),model:e.target.value});setSettings(s);setDraft(s);await refreshStatus()}catch(err){fail(err)}}}>{!(status?.models||[]).some(m=>m.name===settings.model)&&<option value={settings.model}>{settings.model}</option>}{status?.models.map(m=><option key={m.name} value={m.name}>{m.name}</option>)}</select>
                  </div>
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
                        disabled={uploading||(!input.trim()&&!attachmentNames.length)}
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
        ) : page === "workspace" ? (
          <Workspace openChat={openChat} initial={settings.setup_complete?"Today":"Setup"}/>
        ) : page === "learning" ? (
          <LearningLab />

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
                      Automatically update from stable GitHub Releases
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
                <div className="panel"><h2>Personal response preferences</h2><label>Your goals<textarea maxLength={1000} value={draft.goals||""} onChange={e=>setDraft({...draft,goals:e.target.value})} placeholder="What would you like Nila to help you achieve?"/></label><label>Answer detail<select value={draft.response_style||"Balanced"} onChange={e=>setDraft({...draft,response_style:e.target.value})}><option>Concise</option><option>Balanced</option><option>Detailed</option></select></label><small>Used locally when relevant. These preferences are never passed to Gemini Learning Lab.</small></div><label className="check-label knowledge-preference">
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
                    Use saved learning and web knowledge in chat
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

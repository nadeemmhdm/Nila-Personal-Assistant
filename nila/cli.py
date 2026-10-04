import argparse
import asyncio
import json
import sys
import threading
import webbrowser
from . import __version__
from .storage import Store
from .engine import reply, models, NilaError

def parser():
    p = argparse.ArgumentParser(prog="nila",description="Nila Personal Assistant · local Ollama chat")
    p.add_argument("--version",action="version",version=f"Nila {__version__}")
    sub = p.add_subparsers(dest="command")
    ask = sub.add_parser("ask",help="Ask one question")
    ask.add_argument("prompt")
    ask.add_argument("--chat",help="Resume a conversation ID")
    chat = sub.add_parser("chat",help="Interactive conversation")
    chat.add_argument("--chat",help="Resume a conversation ID")
    web = sub.add_parser("web",help="Start the local web interface")
    web.add_argument("--port",type=int,default=8765)
    web.add_argument("--no-open",action="store_true")
    sub.add_parser("doctor",help="Check Ollama, model, and storage")
    sub.add_parser("models",help="List installed Ollama models")
    model = sub.add_parser("model",help="Set the default model")
    model.add_argument("action",choices=["use"])
    model.add_argument("name")
    sub.add_parser("history",help="List conversations")
    delete = sub.add_parser("delete",help="Delete one conversation")
    delete.add_argument("id")
    export = sub.add_parser("export",help="Export conversation to stdout as Markdown")
    export.add_argument("id")
    settings = sub.add_parser("settings",help="Show or update settings")
    settings.add_argument("--name")
    settings.add_argument("--user")
    settings.add_argument("--language",choices=["Auto","English","Malayalam"])
    for kind in ["memory","notes","tasks"]:
        item = sub.add_parser(kind,help=f"Manage {kind}")
        item.add_argument("action",nargs="?",default="list",choices=["list","add","remove","edit","done"] if kind == "tasks" else ["list","add","remove","edit"])
        item.add_argument("value",nargs="?")
        item.add_argument("text",nargs="?")
    return p

async def answer(store,cid,prompt):
    async for part in reply(store,cid,prompt):
        print(part,end="",flush=True)
    print()

async def interactive(store,cid):
    s = store.settings()
    print(f"\n{s['assistant_name']} · {s['model']} · local\nConversation: {cid}\n/exit to quit · /new for a new chat · /remember TEXT to save a fact\n")
    while True:
        try: prompt = input("You › ").strip()
        except EOFError: break
        if prompt == "/exit": break
        if prompt == "/new":
            cid = store.create_chat()["id"]
            print(f"New conversation: {cid}")
            continue
        if prompt.startswith("/remember "):
            value = prompt[10:].strip()
            if value and len(value)<=2000: store.add_item("memories",value); print("Memory saved.")
            else: print("Memory must be 1–2000 characters.")
            continue
        if not prompt: continue
        if len(prompt)>12000: print("Message limit: 12000 characters."); continue
        print(f"{s['assistant_name']} › ",end="",flush=True)
        try: await answer(store,cid,prompt)
        except (NilaError, RuntimeError) as exc: print(f"\n{exc}")

def main():
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    store = Store()
    try:
        if args.command == "web":
            if not 1024 <= args.port <= 65535: raise ValueError("Port must be 1024–65535")
            import uvicorn
            from .server import create_app
            if not args.no_open:
                timer = threading.Timer(1.2,lambda:webbrowser.open(f"http://127.0.0.1:{args.port}"))
                timer.daemon = True
                timer.start()
            uvicorn.run(create_app(store),host="127.0.0.1",port=args.port,log_level="warning")
        elif args.command == "ask":
            prompt = args.prompt.strip()
            if not prompt or len(prompt)>12000: raise ValueError("Message must be 1–12000 characters")
            cid = args.chat or store.create_chat()["id"]
            asyncio.run(answer(store,cid,prompt))
        elif args.command in {"chat",None}:
            cid = getattr(args,"chat",None) or store.create_chat()["id"]
            store.chat(cid)
            asyncio.run(interactive(store,cid))
        elif args.command in {"doctor","models"}:
            if args.command == "doctor":
                print(f"Nila {__version__}\nStorage: {store.root}\nDefault model: {store.settings()['model']}")
            installed = asyncio.run(models())
            for m in installed: print(f"{m['name']}  {m.get('size',0)/1e9:.2f} GB")
            if args.command == "doctor":
                if store.settings()["model"] not in [m["name"] for m in installed]:
                    raise NilaError("NILA-002: Run: ollama pull " + store.settings()["model"])
                print("Ready. Run nila or nila web.")
        elif args.command == "model":
            from .server import Settings
            settings = Settings(**(store.settings() | {"model":args.name}))
            store.save_settings(settings.model_dump())
            print(f"Default model: {args.name}")
        elif args.command == "settings":
            from .server import Settings
            values = store.settings()
            for key,arg in [("assistant_name",args.name),("user_name",args.user),("language",args.language)]:
                if arg is not None: values[key]=arg
            print(json.dumps(store.save_settings(Settings(**values).model_dump()),indent=2,ensure_ascii=False))
        elif args.command == "history":
            for c in store.chats(): print(c["id"],c["title"])
        elif args.command == "delete":
            token = store.acquire()
            try: store.delete_chat(args.id)
            finally: store.release(token)
            print("Conversation deleted.")
        elif args.command == "export":
            c = store.chat(args.id)
            print("# "+c["title"])
            for m in c["messages"]: print(f"\n## {m['role'].title()} ({m['status']})\n\n{m['content']}")
        else:
            kind = {"memory":"memories","notes":"notes","tasks":"tasks"}[args.command]
            if args.action == "list":
                for item in store.items(kind): print(item["id"],("[x] " if item.get("done") else "[ ] ") if kind=="tasks" else "",item["content"])
            elif not args.value: raise ValueError("Provide text for add, or an item ID for other actions")
            elif args.action == "add":
                if not args.value.strip() or len(args.value)>2000: raise ValueError("Item must be 1–2000 characters")
                print(store.add_item(kind,args.value.strip()))
            elif args.action == "remove": store.delete_item(kind,args.value)
            elif args.action == "done": store.update_item(kind,args.value,done=True)
            elif args.action == "edit":
                if not args.text or not args.text.strip() or len(args.text)>2000: raise ValueError("Provide new text (1–2000 characters) after the item ID")
                store.update_item(kind,args.value,content=args.text.strip())
    except KeyboardInterrupt:
        print("\nStopped.")
    except (NilaError, RuntimeError, ValueError, KeyError) as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__": main()

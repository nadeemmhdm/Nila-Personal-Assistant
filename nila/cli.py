import argparse
import asyncio
import json
import sys
import threading
import webbrowser
import getpass
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
    ask.add_argument("--temporary",action="store_true")
    ask.add_argument('--search',choices=['off','quick','deep'],default='off')
    ask.add_argument('--edit',type=int,help='Replace a user message ID in --chat, removing subsequent turns')
    feedback=sub.add_parser('feedback',help='Rate an answer locally; never sent to Gemini')
    feedback.add_argument('chat_id')
    feedback.add_argument('message_id',type=int)
    feedback.add_argument('rating',choices=['up','down','clear'])
    chat = sub.add_parser("chat",help="Interactive conversation")
    chat.add_argument("--chat",help="Resume a conversation ID")
    chat.add_argument("--temporary",action="store_true")
    web = sub.add_parser("web",help="Start the local web interface")
    web.add_argument("--port",type=int,default=8765)
    web.add_argument("--no-open",action="store_true")
    gemini=sub.add_parser("gemini",help="Configure Gemini without exposing the key in command history")
    gemini.add_argument("action",choices=["setup","models","remove","status"])
    learn=sub.add_parser("learn",help="Visible Gemini/Ollama study session")
    learn.add_argument("topic",nargs="?")
    learn.add_argument("--description",default="")
    learn.add_argument("--minutes",type=int,default=15)
    learn.add_argument("--rounds",type=int,default=10)
    learn.add_argument("--gemini-model")
    learn.add_argument("--model")
    learn.add_argument("--consent",action="store_true",help="Allow sending session content to Google")
    learn.add_argument("--no-save",action="store_true")
    learn.add_argument("--list",action="store_true")
    learn.add_argument("--show")
    learn.add_argument("--stop")
    learn.add_argument("--delete")
    kb=sub.add_parser("knowledge",help="Inspect, edit or forget learned study notes")
    kb.add_argument("action",nargs="?",default="list",choices=["list","edit","disable","enable","remove"])
    kb.add_argument("id",nargs="?")
    kb.add_argument("--text")
    sub.add_parser("worker",help="Run offline scheduled tasks until stopped")
    update = sub.add_parser("update",help="Check or install stable GitHub Releases")
    update.add_argument("--check",action="store_true")
    update.add_argument("--auto",action="store_true",help=argparse.SUPPRESS)
    svc=sub.add_parser("service",help="Control the Windows login worker")
    svc.add_argument("action",choices=["start","stop","enable","disable"])
    pull = sub.add_parser("pull",help="Download a local Ollama model")
    pull.add_argument("model",nargs="?",default="llama3.2:1b")
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
    settings.add_argument("--description")
    settings.add_argument("--position",choices=["Student","Employee","Self-employed","Other","Prefer not to say"])
    settings.add_argument("--completion-year")
    settings.add_argument("--company")
    settings.add_argument("--job-role")
    settings.add_argument("--knowledge",choices=["on","off"])
    settings.add_argument("--course")
    settings.add_argument("--interests")
    settings.add_argument("--tone",choices=["Friendly","Professional","Concise"])
    settings.add_argument("--thinking",choices=["low","medium","high"])
    settings.add_argument("--memory-review",choices=["on","off"])
    settings.add_argument("--auto-memory",choices=["on","off"])
    settings.add_argument("--memory",choices=["on","off"])
    settings.add_argument("--auto-update",choices=["on","off"])
    settings.add_argument("--temperature",type=float)
    settings.add_argument("--context",type=int)
    for kind in ["memory"]:
        item = sub.add_parser(kind,help=f"Manage {kind}")
        item.add_argument("action",nargs="?",default="list",choices=["list","add","remove","edit","done"] if kind == "tasks" else ["list","add","remove","edit"])
        item.add_argument("value",nargs="?")
        item.add_argument("text",nargs="?")
    from .workspace_cli import add_parsers
    add_parsers(sub)
    return p

async def answer(store,cid,prompt,search_mode="off",search_query=None,edit_message_id=None):
    from .terminal import render_reply
    await render_reply(store,cid,prompt,search_mode=search_mode,search_query=search_query,edit_message_id=edit_message_id)

async def interactive(store,cid):
    s = store.settings()
    search_mode="off"
    from .terminal import banner,console,render_reply
    banner()
    console.print(f"[dim]Conversation: {cid}[/dim]")
    while True:
        try: prompt = console.input("[bold cyan]You › [/]").strip()
        except EOFError: break
        if prompt == "/exit": break
        if prompt == "/help":
            print('/new · /think low|medium|high · /attach FILE · /regenerate [instructions] · /resume ID · /search off|quick|deep · /continue · /edit · /up · /down · /model · /learn · /remember TEXT · /exit. Or just type a message.')
            continue
        if prompt.startswith('/think '):
            level=prompt.split(maxsplit=1)[1]
            if level not in {'low','medium','high'}:console.print('Choose low, medium or high.');continue
            store.save_settings({'thinking_level':level});console.print('Thinking level: '+level);continue
        if prompt.startswith('/attach '):
            from pathlib import Path
            from .workspace import ingest,attach
            try:
                path=Path(prompt[8:].strip().strip('"'))
                if path.stat().st_size>5*1024*1024:raise ValueError('File limit: 5 MB')
                iid=ingest(store,path.name,path.read_bytes())
                with store.db() as db:ids=[r[0] for r in db.execute('SELECT document_id FROM chat_documents WHERE chat_id=?',(cid,))]
                attach(store,cid,ids+[iid]);console.print('File attached. Ask your question.')
            except (OSError,ValueError) as exc:console.print(str(exc))
            continue
        if prompt=='/regenerate'  or prompt.startswith('/regenerate '):
            last=next((m for m in reversed(store.chat(cid)['messages']) if m['role']=='assistant'),None)
            if not last:print('No answer to regenerate');continue
            instruction=prompt[len('/regenerate'):].strip() or input('What should change? (optional): ').strip()
            if len(instruction)>2000:print('Instruction limit: 2000 characters');continue
            try:
                await render_reply(store,cid,'Regenerate',regenerate_id=last['id'],instruction=instruction,learn_memory=False)
            except (NilaError,RuntimeError) as exc:print(exc)
            continue
        if prompt.startswith('/search '):
            mode=prompt.split(maxsplit=1)[1]
            if mode not in {'off','quick','deep'}: print('Choose off, quick or deep.'); continue
            search_mode=mode
            print('Web search:',mode,'. When enabled only each new message is sent to search services, not chat history or memories.')
            continue
        if prompt.startswith('/resume '):
            try:
                target=prompt.split(maxsplit=1)[1];store.chat(target);cid=target;print('Resumed:',cid)
            except KeyError: print('Conversation not found')
            continue
        if store.ephemeral and (prompt in {'/up','/down'} or prompt.startswith(('/feedback ','/remember '))):print('Temporary chats do not save feedback or memory.');continue
        if prompt in {'/up','/down'}:
            latest=next((m for m in reversed(store.chat(cid)['messages']) if m['role']=='assistant'),None)
            if latest:
                store.feedback(cid,latest['id'],1 if prompt=='/up' else -1,'')
                print('Feedback saved locally. Future replies use it as guidance.')
            else: print('No answer to rate yet.')
            continue
        if prompt=='/continue': prompt='Continue your previous answer from where you left off, without repeating it.'
        edit_id=None
        if prompt=='/edit':
            latest=next((m for m in reversed(store.chat(cid)['messages']) if m['role']=='user'),None)
            if not latest: print('No prompt to edit yet.'); continue
            print('This replaces the last prompt and its answer.')
            prompt=input('New prompt: ').strip();edit_id=latest['id']
        if prompt == "/model":
            try:
                available=await models()
                for index,m in enumerate(available,1):print(f"{index}. {m['name']}")
                choice=input('Model number or name: ').strip()
                name=available[int(choice)-1]['name'] if choice.isdigit() and 1<=int(choice)<=len(available) else choice
                from .server import Settings
                s=store.save_settings(Settings(**(store.settings()|{'model':name})).model_dump())
                print('Using',s['model'])
            except (NilaError,ValueError) as exc:print(exc)
            continue
        if store.ephemeral and prompt=='/learn':print('Learning Lab is unavailable inside temporary chats.');continue
        if prompt == "/learn":
            try:await learning_wizard(store)
            except (RuntimeError,ValueError) as exc:print(exc)
            continue
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
        console.print("[bold bright_magenta]Nila[/]")
        try: await answer(store,cid,prompt,search_mode=search_mode,edit_message_id=edit_id)
        except (NilaError, RuntimeError) as exc: print(f"\n{exc}")

def main():
    if sys.argv[1:]==['_extract_pdf']:
        from .pdf_extract import main as extract
        extract();return
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    argv=sys.argv[1:]
    if argv == ["version"]:argv=["--version"]
    if argv and argv[0] in {"updatw","upadte","udpate"}:argv[0]="update"
    if argv and argv[0] in {'recover'}:
        print('Notes, tasks and automation features have been removed.',file=sys.stderr);raise SystemExit(1)
    known={'ask','chat','web','worker','update','service','pull','doctor','models','model','history','delete','export','settings','memory','gemini','learn','knowledge','feedback'}
    from .workspace_cli import COMMANDS,execute
    known |= COMMANDS
    if argv and not argv[0].startswith('-') and argv[0] not in known:
        argv=['ask',' '.join(argv)]
    args = parser().parse_args(argv)
    store = Store()
    try:
        from .updater import start_auto_update
        if args.command in {None,"chat","ask","web"}: start_auto_update(store)
        if getattr(args,'temporary',False):
            if getattr(args,'chat',None):raise ValueError('Temporary chats cannot resume saved history')
            original=store;store=Store(ephemeral=True)
            store.save_settings({k:v for k,v in original.settings().items() if k in {'assistant_name','model','language','temperature','num_ctx','thinking_level'}}|{'auto_memory':False,'memory_enabled':False,'knowledge_enabled':False,'auto_update':False})
            store.acquire=original.acquire;store.release=original.release
        if args.command in COMMANDS:execute(args,store)
        elif args.command == "gemini":
            from .learning import save_key,delete_key,key,gemini_models
            if args.action=='setup':save_key(store,getpass.getpass('Gemini API key (hidden): '));print('Key saved encrypted. Use nila gemini models to check access.')
            elif args.action=='remove':delete_key(store);print('Key removed. Active sessions will stop.')
            elif args.action=='models':print(json.dumps(asyncio.run(gemini_models(store)),indent=2))
            else:print('Gemini configured' if key(store) else 'No Gemini key saved')
        elif args.command == "learn":
            from .learning import LearningLab,SessionConfig,sessions,session,gemini_models
            lab=LearningLab(store)
            if args.list:print(json.dumps(sessions(store),indent=2,ensure_ascii=False))
            elif args.show:print(json.dumps(session(store,args.show),indent=2,ensure_ascii=False))
            elif args.stop:lab.stop(args.stop);print('Stop requested.')
            elif args.delete:
                if session(store,args.delete)['status']=='running':raise ValueError('Stop session first')
                with store.db() as db:db.execute('DELETE FROM learning_sessions WHERE id=?',(args.delete,));db.execute('DELETE FROM knowledge WHERE session_id=?',(args.delete,))
            else:
                topic=args.topic or input('What would you like the models to discuss? ').strip()
                gm=args.gemini_model
                if not gm:
                    available=asyncio.run(gemini_models(store))
                    for index,m in enumerate(available,1):print(f"{index}. {m['name']}")
                    choice=input('Gemini model number or name: ').strip();gm=available[int(choice)-1]['name'] if choice.isdigit() and 1<=int(choice)<=len(available) else choice
                print('Topic, description and model answers are sent to Google. No profile/chat history is included. Free-tier quotas and Google data policies apply; costs depend on your account. This saves study notes, not model weights.')
                consent=args.consent or input('Start this cloud review session? [y/N] ').strip().lower()=='y'
                config=SessionConfig(topic=topic,description=args.description,local_model=args.model or store.settings()['model'],gemini_model=gm,minutes=args.minutes,max_rounds=args.rounds,save_knowledge=not args.no_save,consent=consent)
                asyncio.run(watch_learning(lab,config))
        elif args.command == "knowledge":
            from .learning import ensure,knowledge
            ensure(store)
            if args.action=='list':print(json.dumps(knowledge(store),indent=2,ensure_ascii=False))
            elif not args.id:raise ValueError('Provide lesson ID')
            else:
                with store.db() as db:
                    if args.action=='remove':db.execute('DELETE FROM knowledge WHERE id=?',(args.id,))
                    elif args.action=='edit':
                        if not args.text or not args.text.strip() or len(args.text)>2000:raise ValueError('Provide --text (1–2000 characters)')
                        db.execute('UPDATE knowledge SET content=? WHERE id=?',(store.seal(args.text.strip()),args.id))
                    else:db.execute('UPDATE knowledge SET enabled=? WHERE id=?',(int(args.action=='enable'),args.id))
        elif args.command == "worker":
            from .worker import run_worker
            asyncio.run(run_worker(store))
        elif args.command == "service":
            from .extensions import service
            print(service(args.action)['message'])
        elif args.command == "update":
            from .updater import check,apply_update,auto_update
            if args.auto: auto_update(store)
            else: print(json.dumps(check() if args.check else apply_update(),indent=2))
        elif args.command == "pull":
            from .extensions import pull_model,ModelPull
            model=ModelPull(model=args.model).model
            asyncio.run(pull_model(model,lambda d:print(d.get('status',''),flush=True)))
        elif args.command == "web":
            if not 1024 <= args.port <= 65535: raise ValueError("Port must be 1024–65535")
            import uvicorn
            from .server import create_app
            if not args.no_open:
                timer = threading.Timer(1.2,lambda:webbrowser.open(f"http://127.0.0.1:{args.port}"))
                timer.daemon = True
                timer.start()
            uvicorn.run(create_app(store),host="127.0.0.1",port=args.port,log_level="warning")
        elif args.command == "feedback":
            store.feedback(args.chat_id,args.message_id,{'up':1,'down':-1,'clear':0}[args.rating],'')
            print('Feedback saved locally.')
        elif args.command == "ask":
            prompt = args.prompt.strip()
            if not prompt or len(prompt)>12000: raise ValueError("Message must be 1–12000 characters")
            cid = args.chat or store.create_chat()["id"]
            if args.edit and not args.chat: raise ValueError("--edit requires --chat")
            asyncio.run(answer(store,cid,prompt,search_mode=args.search,edit_message_id=args.edit))
        elif args.command in {"chat",None}:
            cid = getattr(args,"chat",None) or store.create_chat()["id"]
            store.chat(cid)
            asyncio.run(interactive(store,cid))
        elif args.command in {"doctor","models"}:
            if args.command == "doctor":
                from .extensions import diagnostics
                print(json.dumps(asyncio.run(diagnostics(store)),indent=2,ensure_ascii=False))
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
            for key in ['description','position','completion_year','company','job_role','course','interests','tone','temperature']:
                arg=getattr(args,key)
                if arg is not None:values[key]=arg
            if args.thinking is not None:values['thinking_level']=args.thinking
            if args.context is not None:values['num_ctx']=args.context
            for arg,key in [('memory_review','memory_review'),('auto_memory','auto_memory'),('memory','memory_enabled'),('auto_update','auto_update'),('knowledge','knowledge_enabled')]:
                value=getattr(args,arg)
                if value is not None:values[key]=value=='on'
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
    except (NilaError, RuntimeError, ValueError, KeyError, OSError) as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)

async def learning_wizard(store):
    from .learning import LearningLab,SessionConfig,key,save_key,gemini_models
    if not key(store):save_key(store,getpass.getpass('Gemini API key (hidden): '))
    available=await gemini_models(store)
    for index,m in enumerate(available,1):print(f"{index}. {m['name']}")
    choice=input('Gemini model number or name: ').strip()
    name=available[int(choice)-1]['name'] if choice.isdigit() and 1<=int(choice)<=len(available) else choice
    topic=input('Topic: ').strip();description=input('Description (optional): ').strip()
    minutes=int(input('Time limit in minutes [15]: ').strip() or '15')
    print('This discussion goes to Google; personal chat history/profile are excluded. Free-tier quotas/data terms apply. Saved lessons are model-reviewed notes, not weight training.')
    if input('Start? [y/N] ').strip().lower()!='y':return
    lab=LearningLab(store)
    await watch_learning(lab,SessionConfig(topic=topic,description=description,minutes=minutes,local_model=store.settings()['model'],gemini_model=name,consent=True))

async def watch_learning(lab,config):
    from .learning import session
    iid=lab.start(config);task=lab.tasks[iid];seen=set()
    print(f'Learning session: {iid} · Ctrl+C to stop')
    try:
        while not task.done():
            view=session(lab.store,iid)
            # Print completed turns once; Web UI shows live partial local tokens.
            messages=view['messages']
            for m in messages:
                if m['id'] not in seen and (m['actor']!='ollama' or any(n['round']==m['round'] and n['actor']=='gemini' for n in messages)):
                    print(f"\n[{m['actor']} · round {m['round']}]\n{m['content']}",flush=True);seen.add(m['id'])
            await asyncio.sleep(.4)
        await task
    finally:
        await lab.close()
        view=session(lab.store,iid)
        for m in view['messages']:
            if m['id'] not in seen:print(f"\n[{m['actor']}]\n{m['content']}")
        print('Session:',view['status'],view['error'])

if __name__ == "__main__": main()
